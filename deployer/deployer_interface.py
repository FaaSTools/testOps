
from abc import ABC, abstractmethod
from typing import Dict


class DeployerInterface(ABC):

    @abstractmethod
    def create_storage(self, deployment_dict: Dict, **kwargs):
        """This function should handle the creation of all storages in the deployment_dict"""
        pass

    @abstractmethod
    def upload_function(self, deployment_dict: Dict, **kwargs):
        """This function handles the filetransfer of code packages to cloud storage"""
        pass

    @abstractmethod
    def deploy_function(self, deployment_dict: Dict, **kwargs):
        """This function handles the deployment of all functions and memory configurations in the deployment dict"""
        pass

    @abstractmethod
    def delete_function(self, deployment_dict: Dict, **kwargs):
        """This function handles the deletion of unneeded function after testing them"""
        pass

    @abstractmethod
    def delete_storage(self, deployment_dict: Dict, **kwargs):
        """This function handles the deletion of all cloud storages that were created temporarily"""
        pass

    @abstractmethod
    def deploy_no_op(self, deployment_dict: Dict, **kwargs):
        """This function handles the deployment of a no-op function required to measure Overhead time"""
        pass
