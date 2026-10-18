import os
import boto3
import pytest
from moto import mock_aws

from app.response.cloud_connector import CloudExecutionError, MotoConnector


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@mock_aws
def test_moto_iam_access_key_deactivation_and_rollback(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    iam = session.client("iam")

    # 1. Setup mock user and access key
    username = "attacker-compromised-user"
    iam.create_user(UserName=username)
    key_resp = iam.create_access_key(UserName=username)["AccessKey"]
    key_id = key_resp["AccessKeyId"]
    assert key_resp["Status"] == "Active"

    connector = MotoConnector(session=session)

    # 2. Execute containment: disable access key
    outcome = connector.disable_access_key(username=username, access_key_id=key_id)
    assert outcome.success is True
    assert outcome.pre_state["status"] == "Active"
    assert outcome.post_state["status"] == "Inactive"

    # Verify key is indeed inactive in AWS
    keys = iam.list_access_keys(UserName=username)["AccessKeyMetadata"]
    target_key = next(k for k in keys if k["AccessKeyId"] == key_id)
    assert target_key["Status"] == "Inactive"

    # 3. Rollback: reactivate access key
    rollback_outcome = connector.enable_access_key(username=username, access_key_id=key_id)
    assert rollback_outcome.success is True
    keys = iam.list_access_keys(UserName=username)["AccessKeyMetadata"]
    target_key = next(k for k in keys if k["AccessKeyId"] == key_id)
    assert target_key["Status"] == "Active"


@mock_aws
def test_moto_s3_public_access_block(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    s3 = session.client("s3")

    # 1. Setup mock bucket
    bucket_name = "corp-data-exfiltration-target"
    s3.create_bucket(Bucket=bucket_name)

    connector = MotoConnector(session=session)

    # 2. Block public access
    outcome = connector.block_s3_public_access(bucket_name=bucket_name)
    assert outcome.success is True
    assert outcome.post_state["BlockPublicAcls"] is True
    assert outcome.post_state["BlockPublicPolicy"] is True

    # Verify directly via boto3
    conf = s3.get_public_access_block(Bucket=bucket_name)["PublicAccessBlockConfiguration"]
    assert conf["BlockPublicAcls"] is True
    assert conf["BlockPublicPolicy"] is True
    assert conf["IgnorePublicAcls"] is True
    assert conf["RestrictPublicBuckets"] is True


@mock_aws
def test_moto_detach_rogue_iam_policy(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    iam = session.client("iam")

    username = "developer-escalated"
    iam.create_user(UserName=username)

    # Create dummy policy
    policy_doc = '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}'
    policy_resp = iam.create_policy(PolicyName="AdminPrivilegeEscalation", PolicyDocument=policy_doc)["Policy"]
    policy_arn = policy_resp["Arn"]

    iam.attach_user_policy(UserName=username, PolicyArn=policy_arn)
    attached_before = iam.list_attached_user_policies(UserName=username)["AttachedPolicies"]
    assert any(p["PolicyArn"] == policy_arn for p in attached_before)

    connector = MotoConnector(session=session)

    # Execute detach
    outcome = connector.detach_user_policy(username=username, policy_arn=policy_arn)
    assert outcome.success is True

    attached_after = iam.list_attached_user_policies(UserName=username)["AttachedPolicies"]
    assert not any(p["PolicyArn"] == policy_arn for p in attached_after)
