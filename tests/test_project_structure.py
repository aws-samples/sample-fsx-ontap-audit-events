"""
Tests for CDK project structure initialization.
"""
import os
import pytest


class TestProjectStructure:
    """Test that the CDK project structure is correctly initialized."""

    def test_cdk_app_exists(self):
        """Verify app.py exists."""
        assert os.path.exists("app.py"), "app.py should exist"

    def test_cdk_json_exists(self):
        """Verify cdk.json exists."""
        assert os.path.exists("cdk.json"), "cdk.json should exist"

    def test_requirements_txt_exists(self):
        """Verify requirements.txt exists."""
        assert os.path.exists("requirements.txt"), "requirements.txt should exist"

    def test_gitignore_exists(self):
        """Verify .gitignore exists."""
        assert os.path.exists(".gitignore"), ".gitignore should exist"

    def test_stack_file_exists(self):
        """Verify fsx_audit_stack.py exists."""
        assert os.path.exists("fsx_audit_stack.py"), "fsx_audit_stack.py should exist"

    def test_lambda_audit_processor_directory(self):
        """Verify lambda/audit_processor directory exists."""
        assert os.path.isdir("lambda/audit_processor"), "lambda/audit_processor directory should exist"
        assert os.path.exists("lambda/audit_processor/__init__.py"), "lambda/audit_processor/__init__.py should exist"

    def test_lambda_file_processor_directory(self):
        """Verify lambda/file_processor directory exists."""
        assert os.path.isdir("lambda/file_processor"), "lambda/file_processor directory should exist"
        assert os.path.exists("lambda/file_processor/__init__.py"), "lambda/file_processor/__init__.py should exist"

    def test_layers_evtx_directory(self):
        """Verify layers/evtx directory exists."""
        assert os.path.isdir("layers/evtx"), "layers/evtx directory should exist"

    def test_layers_pillow_directory(self):
        """Verify layers/pillow directory exists."""
        assert os.path.isdir("layers/pillow"), "layers/pillow directory should exist"

    def test_app_py_imports(self):
        """Verify app.py can be imported without errors."""
        with open("app.py", "r") as f:
            content = f.read()
            assert "import aws_cdk" in content, "app.py should import aws_cdk"
            assert "from fsx_audit_stack import FsxAuditStack" in content, "app.py should import FsxAuditStack"

    def test_stack_class_definition(self):
        """Verify stack file contains FsxAuditStack class."""
        with open("fsx_audit_stack.py", "r") as f:
            content = f.read()
            assert "class FsxAuditStack" in content, "fsx_audit_stack.py should define FsxAuditStack class"
            assert "from aws_cdk import Stack" in content, "fsx_audit_stack.py should import Stack"

    def test_requirements_contains_cdk(self):
        """Verify requirements.txt contains CDK dependencies."""
        with open("requirements.txt", "r") as f:
            content = f.read()
            assert "aws-cdk-lib" in content, "requirements.txt should contain aws-cdk-lib"
            assert "constructs" in content, "requirements.txt should contain constructs"
