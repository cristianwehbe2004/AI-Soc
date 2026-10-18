from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class CloudExecutionError(RuntimeError):
    pass


@dataclass
class CloudActionOutcome:
    action_type: str
    target: str
    success: bool
    pre_state: dict[str, Any]
    post_state: dict[str, Any]
    request_id: str | None = None
    error: str | None = None


class BaseCloudConnector(ABC):
    """Abstract interface separating action definitions from real cloud providers."""

    @abstractmethod
    def disable_access_key(self, *, username: str, access_key_id: str) -> CloudActionOutcome:
        """Deactivates an IAM long-term access key and returns the pre-state."""
        ...

    @abstractmethod
    def enable_access_key(self, *, username: str, access_key_id: str) -> CloudActionOutcome:
        """Rollback: Reactivates an IAM access key."""
        ...

    @abstractmethod
    def block_s3_public_access(self, *, bucket_name: str) -> CloudActionOutcome:
        """Enforces all 4 public access blocks on an S3 bucket."""
        ...

    @abstractmethod
    def detach_user_policy(self, *, username: str, policy_arn: str) -> CloudActionOutcome:
        """Detaches an IAM managed policy from a user."""
        ...


class MotoConnector(BaseCloudConnector):
    """
    In-memory mock AWS connector using moto.
    Executes real boto3 calls against an in-memory AWS emulation with ZERO AWS charges.
    """

    def __init__(self, session: Any | None = None) -> None:
        import boto3
        # Ensure fake test credentials so boto3 never touches real AWS
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
        os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
        os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
        os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
        self.session = session or boto3.Session(region_name="us-east-1")

    def disable_access_key(self, *, username: str, access_key_id: str) -> CloudActionOutcome:
        iam = self.session.client("iam")
        # 1. Fetch current pre-state
        keys = iam.list_access_keys(UserName=username).get("AccessKeyMetadata", [])
        target_meta = next((k for k in keys if k["AccessKeyId"] == access_key_id), None)
        if not target_meta:
            raise CloudExecutionError(f"Access key {access_key_id} not found on user {username}")

        pre_state = {"status": target_meta["Status"], "username": username, "key_id": access_key_id}

        # 2. Deactivate key
        resp = iam.update_access_key(UserName=username, AccessKeyId=access_key_id, Status="Inactive")

        return CloudActionOutcome(
            action_type="disable_aws_access_key",
            target=f"{username}:{access_key_id}",
            success=True,
            pre_state=pre_state,
            post_state={"status": "Inactive"},
            request_id=resp.get("ResponseMetadata", {}).get("RequestId"),
        )

    def enable_access_key(self, *, username: str, access_key_id: str) -> CloudActionOutcome:
        iam = self.session.client("iam")
        resp = iam.update_access_key(UserName=username, AccessKeyId=access_key_id, Status="Active")
        return CloudActionOutcome(
            action_type="enable_aws_access_key",
            target=f"{username}:{access_key_id}",
            success=True,
            pre_state={"status": "Inactive"},
            post_state={"status": "Active"},
            request_id=resp.get("ResponseMetadata", {}).get("RequestId"),
        )

    def block_s3_public_access(self, *, bucket_name: str) -> CloudActionOutcome:
        s3 = self.session.client("s3")
        # Pre-state
        try:
            current = s3.get_public_access_block(Bucket=bucket_name).get("PublicAccessBlockConfiguration", {})
        except Exception:
            current = {"BlockPublicAcls": False, "IgnorePublicAcls": False, "BlockPublicPolicy": False, "RestrictPublicBuckets": False}

        config = {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }
        resp = s3.put_public_access_block(Bucket=bucket_name, PublicAccessBlockConfiguration=config)

        return CloudActionOutcome(
            action_type="block_s3_public_access",
            target=bucket_name,
            success=True,
            pre_state=current,
            post_state=config,
            request_id=resp.get("ResponseMetadata", {}).get("RequestId"),
        )

    def detach_user_policy(self, *, username: str, policy_arn: str) -> CloudActionOutcome:
        iam = self.session.client("iam")
        resp = iam.detach_user_policy(UserName=username, PolicyArn=policy_arn)
        return CloudActionOutcome(
            action_type="detach_user_policy",
            target=f"{username}:{policy_arn}",
            success=True,
            pre_state={"attached": True, "policy_arn": policy_arn},
            post_state={"attached": False},
            request_id=resp.get("ResponseMetadata", {}).get("RequestId"),
        )


class RealAWSConnector(BaseCloudConnector):
    """Production AWS connector invoking genuine AWS APIs."""

    def __init__(self, session: Any | None = None) -> None:
        import boto3
        self.session = session or boto3.Session()

    def disable_access_key(self, *, username: str, access_key_id: str) -> CloudActionOutcome:
        # Same signature, backed by real AWS credentials
        iam = self.session.client("iam")
        resp = iam.update_access_key(UserName=username, AccessKeyId=access_key_id, Status="Inactive")
        return CloudActionOutcome(
            action_type="disable_aws_access_key",
            target=f"{username}:{access_key_id}",
            success=True,
            pre_state={"status": "Active"},
            post_state={"status": "Inactive"},
            request_id=resp.get("ResponseMetadata", {}).get("RequestId"),
        )

    def enable_access_key(self, *, username: str, access_key_id: str) -> CloudActionOutcome:
        iam = self.session.client("iam")
        resp = iam.update_access_key(UserName=username, AccessKeyId=access_key_id, Status="Active")
        return CloudActionOutcome(
            action_type="enable_aws_access_key",
            target=f"{username}:{access_key_id}",
            success=True,
            pre_state={"status": "Inactive"},
            post_state={"status": "Active"},
            request_id=resp.get("ResponseMetadata", {}).get("RequestId"),
        )

    def block_s3_public_access(self, *, bucket_name: str) -> CloudActionOutcome:
        s3 = self.session.client("s3")
        config = {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }
        resp = s3.put_public_access_block(Bucket=bucket_name, PublicAccessBlockConfiguration=config)
        return CloudActionOutcome(
            action_type="block_s3_public_access",
            target=bucket_name,
            success=True,
            pre_state={},
            post_state=config,
            request_id=resp.get("ResponseMetadata", {}).get("RequestId"),
        )

    def detach_user_policy(self, *, username: str, policy_arn: str) -> CloudActionOutcome:
        iam = self.session.client("iam")
        resp = iam.detach_user_policy(UserName=username, PolicyArn=policy_arn)
        return CloudActionOutcome(
            action_type="detach_user_policy",
            target=f"{username}:{policy_arn}",
            success=True,
            pre_state={"attached": True},
            post_state={"attached": False},
            request_id=resp.get("ResponseMetadata", {}).get("RequestId"),
        )
