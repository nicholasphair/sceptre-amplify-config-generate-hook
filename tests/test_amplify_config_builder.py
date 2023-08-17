# -*- coding: utf-8 -*-
from moto import mock_cognitoidp, mock_cognitoidentity
from unittest import TestCase, mock


import boto3
import pytest
from sceptre.connection_manager import ConnectionManager
import os

from hook.amplify_config_builder import AmplifyConfigBuilder


@mock_cognitoidp
@mock_cognitoidentity
class TestAmplifyConnfigBuilder:
    def bootstrap_environment(self):
        """Mocked AWS Credentials for moto."""
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    # NB (nphair): Have not gotten this to play nice with fixtures.
    def bootstrap_userpool(self):
        self.bootstrap_environment()
        cognito_idp = boto3.client("cognito-idp", region_name="us-east-1")
        user_pool_name = "MyUserPool"
        policies = {
            "PasswordPolicy": {
                "MinimumLength": 8,
                "RequireUppercase": True,
                "RequireLowercase": True,
                "RequireNumbers": True,
                "RequireSymbols": True,
            }
        }
        schema = [
            {"Name": "email", "AttributeDataType": "String", "Required": True},
            {
                "Name": "custom_attribute",
                "AttributeDataType": "String",
                "Required": False,
            },
        ]
        auto_verified_attributes = ["email"]

        # Create the user pool
        response = cognito_idp.create_user_pool(
            PoolName=user_pool_name,
            Policies=policies,
            Schema=schema,
            AutoVerifiedAttributes=auto_verified_attributes,
        )

        return response["UserPool"]["Id"]

    def teardown_userpool(self, upid):
        cognito_idp = boto3.client("cognito-idp", region_name="us-east-1")
        cognito_idp.delete_user_pool(UserPoolId=upid)

    def bootstrap_userpool_client(self, upid):
        client = boto3.client("cognito-idp", region_name="us-east-1")
        client_name = "MyUserPoolClient"
        generate_secret = False

        response = client.create_user_pool_client(
            UserPoolId=upid,
            ClientName=client_name,
            GenerateSecret=generate_secret,
            CallbackURLs=[],
        )

        # Print the user pool client details
        user_pool_client_id = response["UserPoolClient"]["ClientId"]
        # user_pool_client_name = response['UserPoolClient']['ClientName']
        return user_pool_client_id

    def teardown_userpool_client(self, upid, client_id):
        cognito_idp = boto3.client("cognito-idp", region_name="us-east-1")
        cognito_idp.delete_user_pool_client(UserPoolId=upid, ClientId=client_id)

    def bootstrap_userpool_domain(self, upid):
        domain = "Myuser-pool-domain"
        client = boto3.client("cognito-idp", region_name="us-east-1")
        client.create_user_pool_domain(
            Domain=domain,
            UserPoolId=upid,
        )
        return domain

    def teardown_userpool_domain(self, upid, domain):
        client = boto3.client("cognito-idp", region_name="us-east-1")
        client.delete_user_pool_domain(
            Domain=domain,
            UserPoolId=upid,
        )

    def bootstrap_identity_pool(self):
        self.bootstrap_environment()
        client = boto3.client("cognito-identity", region_name="us-east-1")

        identity_pool_name = "MyIdentityPool"
        allow_unauthenticated_identities = True

        return client.create_identity_pool(
            IdentityPoolName=identity_pool_name,
            AllowUnauthenticatedIdentities=allow_unauthenticated_identities,
        )["IdentityPoolId"]

    def teardown_identity_pool(self, ipid):
        """Delete not implemented in moto."""
        ## client = boto3.client("cognito-identity", region_name="us-east-1")
        ## client.delete_identity_pool(
        ##     IdentityPoolId=ipid,
        ## )

    def test_fetch_userpool(self):
        user_pool_id = self.bootstrap_userpool()

        connection = ConnectionManager("us-east-1")
        confbuilder = AmplifyConfigBuilder(connection_manager=connection, prefix="My")
        fetched_id = confbuilder.fetch_user_pool()["Id"]

        assert fetched_id == user_pool_id

        self.teardown_userpool(user_pool_id)

    def test_fetch_userpool_client(self):
        user_pool_id = self.bootstrap_userpool()
        client_id = self.bootstrap_userpool_client(user_pool_id)

        connection = ConnectionManager("us-east-1")
        confbuilder = AmplifyConfigBuilder(connection_manager=connection, prefix="My")
        fetched_client = confbuilder.fetch_user_pool_client(user_pool_id=user_pool_id)
        fetched_client_id = fetched_client["ClientId"]
        fetched_user_pool_id = fetched_client["UserPoolId"]

        assert fetched_user_pool_id == user_pool_id
        assert fetched_client_id == client_id

        self.teardown_userpool_client(user_pool_id, client_id)
        self.teardown_userpool(user_pool_id)

    def test_fetch_userpool_domain(self):
        user_pool_id = self.bootstrap_userpool()
        domain = self.bootstrap_userpool_domain(user_pool_id)

        connection = ConnectionManager("us-east-1")
        confbuilder = AmplifyConfigBuilder(connection_manager=connection, prefix="My")
        fetched = confbuilder.fetch_user_pool_domain()

        fetched_domain = fetched["DomainDescription"]["Domain"]
        fetched_user_pool_id = fetched["DomainDescription"]["UserPoolId"]

        assert fetched_domain == domain
        assert fetched_user_pool_id == user_pool_id

        self.teardown_userpool_domain(user_pool_id, domain)
        self.teardown_userpool(user_pool_id)

    def test_fetch_identity_pool(self):
        pool_id = self.bootstrap_identity_pool()

        connection = ConnectionManager("us-east-1")
        unpatched_call = connection.call
        confbuilder = AmplifyConfigBuilder(connection_manager=connection, prefix="My")

        with mock.patch.object(connection, "call") as mock_method:

            def side_effect(service, command, kwargs):
                if service == "cognito-identity" and command == "list_identity_pools":
                    return {
                        "IdentityPools": [
                            {
                                "IdentityPoolId": pool_id,
                                "IdentityPoolName": "MyIdentityPool",
                            },
                        ]
                    }
                return unpatched_call(service, command, kwargs)

            mock_method.side_effect = side_effect

            fetched = confbuilder.fetch_identity_pool()

        fetched_id = fetched["IdentityPoolId"]
        assert pool_id == fetched_id

        self.teardown_identity_pool(pool_id)

    def test_build(self):
        user_pool_id = self.bootstrap_userpool()
        client_id = self.bootstrap_userpool_client(user_pool_id)
        domain = self.bootstrap_userpool_domain(user_pool_id)
        idpool_id = self.bootstrap_identity_pool()

        connection = ConnectionManager("us-east-1")
        unpatched_call = connection.call
        confbuilder = AmplifyConfigBuilder(connection_manager=connection, prefix="My")

        with mock.patch.object(connection, "call") as mock_method:

            def side_effect(service, command, kwargs):
                if service == "cognito-identity" and command == "list_identity_pools":
                    return {
                        "IdentityPools": [
                            {
                                "IdentityPoolId": idpool_id,
                                "IdentityPoolName": "MyIdentityPool",
                            },
                        ]
                    }
                return unpatched_call(service, command, kwargs)

            mock_method.side_effect = side_effect

            config = confbuilder.build()

        assert config

        self.teardown_userpool_domain(user_pool_id, domain)
        self.teardown_userpool_client(user_pool_id, client_id)
        self.teardown_userpool(user_pool_id)
        self.teardown_identity_pool(idpool_id)
