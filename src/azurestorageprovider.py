"""Provides a way to upload video content to Azure Storage."""

from azure.storage.blob import BlockBlobService, ContentSettings


class AzureStorageProvider(object):
    """Class that facilitates connection to Azure Storage."""

    def upload_video(self, account_name='', sas_token='',
                     container='', blob='', path=''):
        """Upload video to the provided account."""

        block_blob_service = None

        if account_name and sas_token and container and blob:
            block_blob_service = BlockBlobService(
                account_name=account_name, sas_token=sas_token)
            containers = block_blob_service.list_containers()

            print("Available containers:")
            for container_entry in containers:
                print(container_entry.name)

            container_matches = any(
                x for x in containers if x.name == container)

            if not container_matches:
                block_blob_service.create_container(container)
        else:
            print('ERROR: No account credentials for Azure Storage specified.')

        block_blob_service.create_blob_from_path(
            container,
            blob,
            path,
            content_settings=ContentSettings(content_type='video/mp4')
        )
