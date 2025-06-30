import pandas as pd
import psycopg2
import logging
import os
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient
from azure.core.credentials import AccessToken
from azure.core.exceptions import HttpResponseError

# Configure logging with detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Azure storage configuration
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "stdev12311231eastus")
FILE_SYSTEM_NAME = "data"
FILE_PATH = "cars.parquet"
LOCAL_FILE = "cars.parquet"

def log_environment_variables():
    """Log Azure-related environment variables for debugging."""
    azure_vars = {key: value for key, value in os.environ.items() if key.startswith("AZURE_")}
    if azure_vars:
        logger.debug("🔍 Azure environment variables: %s", azure_vars)
    else:
        logger.warning("⚠️ No Azure-related environment variables found")

def print_identity_details(credential):
    """Log detailed information about the identity used."""
    try:
        token: AccessToken = credential.get_token("https://storage.azure.com/.default")
        logger.info("🔐 Identity token obtained")
        logger.debug("🔸 Token (first 40 chars): %s...", token.token[:40])
        logger.debug("🔸 Token expires at: %s", token.expires_on)
        logger.debug("🔸 Credential type: %s", type(credential).__name__)
        # Log all credential sources attempted by DefaultAzureCredential
        if isinstance(credential, DefaultAzureCredential):
            for cred in credential._credential_providers:
                logger.debug("🔸 Available credential provider: %s", type(cred).__name__)
    except Exception as e:
        logger.error("❌ Failed to obtain token from DefaultAzureCredential: %s", str(e))

def check_file_permissions(file_system_client, file_path):
    """Check ACLs for the target file or directory."""
    try:
        file_client = file_system_client.get_file_client(file_path)
        acls = file_client.get_access_control()
        logger.debug("🔍 ACLs for %s: %s", file_path, acls)
        return acls
    except HttpResponseError as e:
        logger.error("❌ Failed to get ACLs for %s: %s", file_path, str(e))
        logger.error("🔍 Request ID: %s", e.response.headers.get("x-ms-request-id"))
        logger.error("🔍 Error code: %s", e.error_code)
        return None

def get_adls_service_client():
    """Initialize DataLakeServiceClient with diagnostics."""
    credential = DefaultAzureCredential()
    log_environment_variables()
    logger.info("🔎 Initializing ADLS client with identity:")
    print_identity_details(credential)

    try:
        service_client = DataLakeServiceClient(
            account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.dfs.core.windows.net",
            credential=credential
        )
        logger.debug("✅ DataLakeServiceClient initialized")
        return service_client, credential
    except Exception as ex:
        logger.error("❌ Failed to initialize DataLakeServiceClient: %s", str(ex))
        raise

def main():
    """Main function to export data and upload to ADLS."""
    # PostgreSQL connection
    try:
        conn = psycopg2.connect(
            host="postgres",
            port=5432,
            user="marketplace_user",
            password="marketplace_user",
            dbname="postgres"
        )
        logger.info("✅ Connected to PostgreSQL")
    except Exception as e:
        logger.error("❌ Failed to connect to PostgreSQL: %s", str(e))
        raise

    # Export data to Parquet
    logger.info("Starting export from PostgreSQL to Parquet...")
    query = "SELECT * FROM marketplace.cars;"
    try:
        df = pd.read_sql_query(query, conn)
        df.to_parquet(LOCAL_FILE, index=False)
        logger.info("✅ Exported to %s", LOCAL_FILE)
    except Exception as e:
        logger.error("❌ Failed to export to Parquet: %s", str(e))
        raise
    finally:
        conn.close()
        logger.debug("🔒 PostgreSQL connection closed")

    # Upload to ADLS
    logger.info("Uploading %s to Azure Data Lake...", LOCAL_FILE)
    service_client, credential = get_adls_service_client()
    file_system_client = service_client.get_file_system_client(file_system=FILE_SYSTEM_NAME)

    # Check file system permissions
    logger.info("🔍 Checking file system permissions for %s", FILE_SYSTEM_NAME)
    check_file_permissions(file_system_client, "/")

    # Ensure file system exists
    try:
        file_system_client.create_file_system()
        logger.info("Created filesystem: %s", FILE_SYSTEM_NAME)
    except HttpResponseError:
        logger.info("Filesystem %s already exists", FILE_SYSTEM_NAME)

    file_client = file_system_client.get_file_client(FILE_PATH)
    logger.debug("📂 File system URL: %s", file_system_client.url)
    logger.debug("📄 File client URL: %s", file_client.url)
    logger.info("Uploading to URL: https://%s.dfs.core.windows.net/%s/%s",
                AZURE_STORAGE_ACCOUNT_NAME, FILE_SYSTEM_NAME, FILE_PATH)

    # Check file permissions before upload
    logger.info("🔍 Checking permissions for %s", FILE_PATH)
    check_file_permissions(file_system_client, FILE_PATH)

    try:
        logger.info("🔎 Uploading with identity:")
        print_identity_details(credential)  # Use the credential from get_adls_service_client
        with open(LOCAL_FILE, "rb") as data:
            file_client.upload_data(data, overwrite=True)
        logger.info("✅ Uploaded %s to ADLS Gen2", FILE_PATH)
    except HttpResponseError as e:
        logger.error("❌ Failed to upload to ADLS: %s", str(e))
        logger.error("🔍 Request ID: %s", e.response.headers.get("x-ms-request-id"))
        logger.error("🔍 Error code: %s", e.error_code)
        raise
    except Exception as e:
        logger.error("❌ Unexpected error during upload: %s", str(e))
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error("❌ Script failed: %s", str(e))
        exit(1)