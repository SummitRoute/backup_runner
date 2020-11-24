#!/usr/bin/env python3

from aws_cdk import core

from backup_runner.backup_runner_stack import BackupRunnerStack


app = core.App()
BackupRunnerStack(app, "backup-runner", env={'region': 'us-east-1'})

app.synth()
