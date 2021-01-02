from aws_cdk import (
    aws_iam as iam,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_events as events,
    aws_events_targets as targets,
    aws_efs as efs,
    aws_backup as backup,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns_subscriptions as subscriptions,
    aws_lambda as aws_lambda,
    core,
)


class BackupRunnerStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Get config value for alert email
        email = self.node.try_get_context("email")
        if email == 'changeme@localhost':
            exit('ERROR: Change the email in cdk.json or pass it with -c email=changeme@localhost')

        # Create SNS for alarms to be sent to
        alarm_topic = sns.Topic(self, "backup_alarm", display_name="backup_alarm")

        # Subscribe my email so the alarms go to me
        alarm_topic.add_subscription(
            subscriptions.EmailSubscription(email)
        )

        # Create VPC to run everything in. We make this public just because we don't
        # want to spend $30/mo on a NAT gateway.
        vpc = ec2.Vpc(
            self,
            "VPC",
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public", subnet_type=ec2.SubnetType.PUBLIC
                )
            ],
        )

        ecs_sg = ec2.SecurityGroup(self, "ecs_sg", vpc=vpc)
        efs_sg = ec2.SecurityGroup(self, "efs_sg", vpc=vpc)
        efs_sg.add_ingress_rule(
            peer=ecs_sg,
            connection=ec2.Port.tcp(2049),
            description="Allow backup runner access",
        )
        # Open this to the VPC
        efs_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4("10.0.0.0/8"),
            connection=ec2.Port.tcp(2049),
            description="Allow backup runner access",
        )

        # Define the EFS
        fileSystem = efs.FileSystem(
            self,
            "MyEfsFileSystem",
            vpc=vpc,
            encrypted=True,
            lifecycle_policy=efs.LifecyclePolicy.AFTER_7_DAYS,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            security_group=efs_sg,
        )

        # Define the ECS task
        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)
        taskDefinition = ecs.FargateTaskDefinition(
            self,
            "taskDefinition",
            volumes=[
                ecs.Volume(
                    name="efsvolume",
                    efs_volume_configuration=ecs.EfsVolumeConfiguration(
                        file_system_id=fileSystem.file_system_id,
                        root_directory="/",
                        transit_encryption="ENABLED",
                    ),
                )
            ],
            memory_limit_mib=8192,
            cpu=2048,
        )

        log_driver = ecs.AwsLogDriver(
            stream_prefix="backup_runner", log_retention=logs.RetentionDays.TWO_WEEKS,
        )

        taskDefinition.add_container(
            "backup-runner",
            image=ecs.ContainerImage.from_asset("./resources/backup_runner"),
            memory_limit_mib=8192,
            cpu=2048,
            logging=log_driver,
        )

        # The previous method to add the container doesn't let us specify the mount point for the EFS,
        # so we have to do it here, and referencing the container that was just added.
        taskDefinition.default_container.add_mount_points(
            ecs.MountPoint(
                container_path="/mnt/efs", read_only=False, source_volume="efsvolume"
            )
        )

        # Create rule to trigger this be run every 24 hours
        events.Rule(
            self,
            "scheduled_run",
            rule_name="backup_runner",
            # Run at 2am EST (6am UTC) every night
            schedule=events.Schedule.expression("cron(0 0 * * ? *)"),
            description="Starts the backup runner task every night",
            targets=[
                targets.EcsTask(
                    cluster=cluster,
                    task_definition=taskDefinition,
                    subnet_selection=ec2.SubnetSelection(
                        subnet_type=ec2.SubnetType.PUBLIC
                    ),
                    platform_version=ecs.FargatePlatformVersion.VERSION1_4,  # Required to use EFS
                    # Because "Latest" does not yet support EFS
                    security_groups=[ecs_sg],
                )
            ],
        )

        # Create notification topic for backups
        backup_topic = sns.Topic(self, "backup_topic", display_name="Backup status")

        # Create AWS Backup
        vault = backup.BackupVault(
            self,
            "Vault",
            access_policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.DENY,
                        actions=[
                            "backup:DeleteBackupVault",
                            "backup:DeleteRecoveryPoint",
                            "backup:UpdateRecoveryPointLifecycle",
                            # "backup:PutBackupVaultAccessPolicy", # This results in "Failed putting policy for Backup vault backuprunnerVaultXXX as it will lock down from further policy changes"
                            "backup:DeleteBackupVaultAccessPolicy",
                            "backup:DeleteBackupVaultNotifications",
                            # "backup:PutBackupVaultNotifications", # This causes oher part of this app to fail.
                        ],
                        resources=["*"],
                        principals=[iam.AnyPrincipal()],
                    )
                ]
            ),
            notification_topic=alarm_topic,
            notification_events=[
                # Monitor for some failures or access to the backups
                backup.BackupVaultEvents.BACKUP_JOB_EXPIRED,
                backup.BackupVaultEvents.BACKUP_JOB_FAILED,
                backup.BackupVaultEvents.COPY_JOB_FAILED,
                backup.BackupVaultEvents.COPY_JOB_FAILED,
                backup.BackupVaultEvents.COPY_JOB_STARTED,
                backup.BackupVaultEvents.RESTORE_JOB_COMPLETED,
                backup.BackupVaultEvents.RESTORE_JOB_FAILED,
                backup.BackupVaultEvents.RESTORE_JOB_STARTED,
                backup.BackupVaultEvents.RESTORE_JOB_SUCCESSFUL,
            ],
        )

        plan = backup.BackupPlan.daily35_day_retention(self, "backup")
        plan.add_selection(
            "Selection",
            resources=[backup.BackupResource.from_efs_file_system(fileSystem)],
        )

        #
        # Create metric filter for errors in the CloudWatch Logs from the ECS
        #
        METRIC_NAME = "log_errors"
        METRIC_NAMESPACE = "backup_runner"

        metric = cloudwatch.Metric(namespace=METRIC_NAMESPACE, metric_name=METRIC_NAME)

        error_metric = logs.MetricFilter(
            self,
            "MetricFilterId",
            metric_name=METRIC_NAME,
            metric_namespace=METRIC_NAMESPACE,
            log_group=log_driver.log_group,
            filter_pattern=logs.FilterPattern.any_term("ERROR"),
            metric_value="1",
        )

        error_alarm = cloudwatch.Alarm(
            self,
            "AlarmId",
            metric=metric,
            evaluation_periods=1,
            actions_enabled=True,
            alarm_name="backuper_runner_alarm",
            alarm_description="Errors in backup runner",
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            period=core.Duration.hours(1),
            threshold=1,
            statistic="sum",
        )

        # Connect the alarm to the SNS
        error_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarm_topic))

        # The above doesn't give it privileges, so add them to the alarm topic resource policy.
        alarm_topic.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sns:Publish"],
                resources=[alarm_topic.topic_arn],
                principals=[iam.ServicePrincipal("cloudwatch.amazonaws.com")],
            )
        )
