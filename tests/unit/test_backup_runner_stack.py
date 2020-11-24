import json
import pytest

from aws_cdk import core
from backup_runner.backup_runner_stack import BackupRunnerStack


def get_template():
    app = core.App()
    BackupRunnerStack(app, "backup-runner")
    return json.dumps(app.synth().get_stack("backup-runner").template)


def test_sqs_queue_created():
    assert("AWS::SQS::Queue" in get_template())


def test_sns_topic_created():
    assert("AWS::SNS::Topic" in get_template())
