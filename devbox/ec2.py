import boto3
import logging
import os
from botocore.exceptions import ClientError
from devbox.retry import retry

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)


def get_ec2_resource():
    """
    :return: A Boto3 Amazon EC2 resource. This high-level resource
             is used to create additional high-level objects
             that wrap low-level Amazon EC2 service actions.
    """
    return boto3.resource("ec2")


def get_ec2_instance_resource(instance_id):
    """
    :param boto3_resource: A Boto3 Amazon EC2 resource.
    :param instance_id: The ID of the instance to retrieve.
    :return: The instance object.
    """
    boto3_resource = get_ec2_resource()

    try:
        resource = boto3_resource.Instance(instance_id)
    except ClientError as e:
        logger.error(f"Error getting EC2 instance resource: {str(e)}")
        return None
    except ValueError as ve:
        if "Required parameter" in str(ve):
            logger.error(f"No instance ID was found for the lookup operation")
            return None
    return resource


def get_ec2_client():
    """
    :return: A Boto3 Amazon EC2 client. This low-level client
             is used to make low-level Amazon EC2 service calls.
    """
    return boto3.client("ec2")


def get_ec2_instance_id_by_name(instance_name):
    """
    Returns an EC2 dictionary by Name tag
    """
    ec2 = get_ec2_client()
    try:
        response = ec2.describe_instances(
            Filters=[{"Name": "tag:Name", "Values": [instance_name]}]
        )
    except Exception as e:
        logger.error(f"Error getting EC2 instance by name: {instance_name}: {str(e)}")
        return None
    if response["Reservations"] == []:
        logger.error(f"No EC2 instance found by name: {instance_name}")
        return None
    if len(response["Reservations"]) > 1:
        logger.error(f"Multiple EC2 instances found by name: {instance_name}")
        return None
    return response["Reservations"][0]["Instances"][0]["InstanceId"]


def get_security_group(id: str):
    """
    :param id: The ID of the security group to retrieve.
    :return: The security group object.
    """
    return get_ec2_resource().SecurityGroup(id)


@retry(report=logger.info)
def get_instance_public_ip(instance_resource):
    """
    :param instance_resource: The instance object.
    :return: The public IP address of the instance.
    """
    ip = instance_resource.public_ip_address
    if ip is None:
        raise Exception("No public IP address found")
    return ip


def start_instance(instance_name: str, my_ip: str):
    """Starts dev box and authorize ingress on port 22 for the `my_ip`."""
    logger.info(f"1. Getting EC2 Instance by name {instance_name}...")
    instance_id = get_ec2_instance_id_by_name(instance_name)
    instance = get_ec2_instance_resource(instance_id)
    if instance is None:
        return None, None
    logger.info(f"2. Starting EC2 Instance: {instance_id}...")
    instance.start()
    logger.info(f"3. Waiting for EC2 Instance to start: {instance_id}...")
    instance.wait_until_running()
    logger.info(
        f"4. Getting Security Group by ID: {instance.security_groups[0]['GroupId']}..."
    )
    security_group = get_security_group(instance.security_groups[0]["GroupId"])
    logger.info(f"5. Authorizing ingress on port 22 for IP: {my_ip}...")
    authorize_ingress(security_group, my_ip)
    public_ip = get_instance_public_ip(instance)
    return instance_id, public_ip


def stop_instance(instance_name: str):
    """Stops dev box."""
    logger.info(f"1. Getting EC2 Instance by name {instance_name}...")
    instance_id = get_ec2_instance_id_by_name(instance_name)
    instance = get_ec2_instance_resource(instance_id)
    if instance is None:
        return None
    logger.info(f"2. Stopping EC2 Instance: {instance_id}...")
    instance.stop()
    logger.info(f"3. Waiting for EC2 Instance to stop: {instance_id}...")
    instance.wait_until_stopped()
    return instance_id


def get_instance_status(instance_name: str):
    """
    :param instance_name: The name of the instance to retrieve.
    :return: The status of the instance.
    """
    instance_id = get_ec2_instance_id_by_name(instance_name)
    instance = get_ec2_instance_resource(instance_id)
    if instance is None:
        return None, None
    if instance.state["Name"] == "stopped":
        return "stopped", "0.0.0.0"
    public_ip = get_instance_public_ip(instance)
    return instance.state["Name"], public_ip


def reboot_instance(instance_name: str):
    """Reboots dev box."""
    logger.info(f"1. Getting EC2 Instance by name {instance_name}...")
    instance_id = get_ec2_instance_id_by_name(instance_name)
    instance = get_ec2_instance_resource(instance_id)
    if instance is None:
        return None
    logger.info(f"2. Rebooting EC2 Instance: {instance_id}")
    instance.reboot()
    return instance_id


def authorize_ingress(security_group, ssh_ingress_ip: str):
    """
    Adds a rule to the security group to allow access to SSH.
    """
    if security_group is None:
        logger.info("No security group to update.")
        return

    try:
        ip_permissions = [
            {
                # SSH ingress open to only the specified IP address.
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": f"{ssh_ingress_ip}/32"}],
            }
        ]
        response = security_group.authorize_ingress(IpPermissions=ip_permissions)
    except ClientError as err:

        if err.response["Error"]["Code"] == "InvalidPermission.Duplicate":
            logger.info("Inbound rules already exist. Nothing to do.")
            return None
        logger.error(
            "Couldn't authorize inbound rules for %s. Here's why: %s: %s",
            security_group.id,
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise
    else:
        return response
