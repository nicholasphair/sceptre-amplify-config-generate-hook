from hook.model.amplify_config import *

from sceptre.connection_manager import ConnectionManager


class AmplifyConfigBuilder:
    """
    Dynamically builds an Amplify configuration by querying cognito api.

    Precondition: The cognito resources were deployed.

    Note: I could not find all the values by querying cognito so some configurations are sensible defaults.
    """

    def fetch_user_pool(self):
        """Return a description of the first user that matches a prefix."""
        listing = self.cm.call("cognito-idp", "list_user_pools", {"MaxResults": 60})
        user_pool = [
            up
            for up in listing.get("UserPools", [])
            if up["Name"].startswith(self.prefix)
        ][0]
        user_pool_id = user_pool["Id"]

        description = self.cm.call(
            "cognito-idp", "describe_user_pool", {"UserPoolId": user_pool_id}
        )
        return description["UserPool"]

    def fetch_user_pool_client(self, user_pool_id):
        listing = self.cm.call(
            "cognito-idp",
            "list_user_pool_clients",
            {"UserPoolId": user_pool_id, "MaxResults": 60},
        )
        client = listing.get("UserPoolClients")[0]
        client_id = client["ClientId"]

        client_description = self.cm.call(
            "cognito-idp",
            "describe_user_pool_client",
            {"UserPoolId": user_pool_id, "ClientId": client_id},
        )
        return client_description["UserPoolClient"]

    def fetch_user_pool_domain(self):
        domain = self.cm.call(
            "cognito-idp",
            "describe_user_pool_domain",
            {"Domain": f"{self.prefix}-user-pool-domain"},
        )
        return domain

    def fetch_identity_pool(self):
        listing = self.cm.call(
            "cognito-identity", "list_identity_pools", {"MaxResults": 60}
        )
        identity_pool = [
            idp
            for idp in listing["IdentityPools"]
            if idp["IdentityPoolName"].startswith(self.prefix)
        ][0]
        identity_pool_id = identity_pool["IdentityPoolId"]

        description = self.cm.call(
            "cognito-identity",
            "describe_identity_pool",
            {"IdentityPoolId": identity_pool_id},
        )
        return description

    def build(self):
        user_pool = self.fetch_user_pool()
        user_pool_id = user_pool["Id"]
        user_pool_client = self.fetch_user_pool_client(user_pool_id)
        user_pool_domain = self.fetch_user_pool_domain()
        identity_pool = self.fetch_identity_pool()

        password_settings = PasswordProtectionSettings(
            passwordPolicyMinLength=8, passwordPolicyCharacters=[]
        )

        domain = user_pool_domain["DomainDescription"]["Domain"]
        domain = f"{domain}.auth.{self.cm.region}.amazoncognito.com"
        oauth = OAuth(
            WebDomain=domain,
            AppClientId=user_pool_client.get("ClientId", ""),
            SignInRedirectURI=",".join(user_pool_client.get("CallbackURLs", [])),
            SignOutRedirectURI=",".join(user_pool_client.get("LogoutURLs", [])),
            Scopes=user_pool_client.get("AllowedOAuthScopes", []),
        )

        auth_default = AuthDefault(
            OAuth=oauth,
            authenticationFlowType="USER_SRP_AUTH",  # NB: Could not find in API calls.
            socialProviders=[],
            usernameAttributes=[],
            signupAttributes=["EMAIL", "NAME"],  # NB: Could not find in API calls.
            passwordProtectionSettings=password_settings,
            mfaConfiguration=user_pool["MfaConfiguration"],
            mfaTypes=["SMS"],  # NB: Could not find in API calls.
            verificationMechanisms=["EMAIL"],  # NB: Could not find in API calls.
        )

        auth_class = AuthClass(Default=auth_default)

        cognito_userpool_default = CognitoUserPoolDefault(
            PoolId=user_pool_id,
            AppClientId=user_pool_client["ClientId"],
            Region=self.cm.region,
        )

        cognito_user_pool = CognitoUserPool(Default=cognito_userpool_default)

        cognito_identity_default = CognitoIdentityDefault(
            PoolId=identity_pool["IdentityPoolId"], Region=self.cm.region
        )

        credential_provider = CredentialsProvider(
            CognitoIdentity=CognitoIdentity(Default=cognito_identity_default)
        )

        identity_manager = IdentityManager(Default={})

        auth_plugin = AwsCognitoAuthPlugin(
            UserAgent="aws-amplify-cli/0.1.0",
            Version="0.1.0",
            IdentityManager=identity_manager,
            CredentialsProvider=credential_provider,
            CognitoUserPool=cognito_user_pool,
            Auth=auth_class,
        )

        plugins = Plugins(awsCognitoAuthPlugin=auth_plugin)

        auth = Auth(plugins=plugins)

        config = AmplifyConfiguration(
            UserAgent="aws-amplify-cli/2.0", Version="1.0", auth=auth
        )

        return config

    def __init__(self, connection_manager: ConnectionManager, prefix):
        self.cm = connection_manager
        self.prefix = prefix
