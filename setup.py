import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="backup_runner",
    version="1.0.0",

    description="Runs a nightly backup to an EFS",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Scott Piper",

    package_dir={"": "backup_runner"},
    packages=setuptools.find_packages(where="backup_runner"),

    install_requires=[
        "aws-cdk.core==1.73.0",
        "aws-cdk.aws_iam==1.73.0",
        "aws-cdk.aws_sqs==1.73.0",
        "aws-cdk.aws_sns==1.73.0",
        "aws-cdk.aws_sns_subscriptions==1.73.0",
        "aws-cdk.aws_s3==1.73.0",
        "aws-cdk.aws_ec2==1.73.0",
        "aws-cdk.aws_ecs==1.73.0",
        "aws-cdk.aws_logs==1.73.0",
        "aws-cdk.aws_events==1.73.0",
        "aws-cdk.aws_events_targets==1.73.0",
        "aws-cdk.aws_efs==1.73.0",
        "aws-cdk.aws_backup==1.73.0",
        "aws-cdk.aws_cloudwatch==1.73.0",
        "aws-cdk.aws_cloudwatch_actions==1.73.0",
        "aws-cdk.aws_lambda==1.73.0",
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 5 - Production/Stable",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
