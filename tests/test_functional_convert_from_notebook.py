import subprocess
import tempfile
from os.path import join, exists

import pytest

from mlvtool.conf.conf import DEFAULT_CONF_FILENAME
from mlvtool.exception import MlVToolException
from mlvtool.ipynb_to_python import IPynbToPython
from tests.helpers.utils import gen_notebook, write_conf


def is_in(expected: str, file_content: str):
    sanitized_expected = expected.replace('\n', '').replace(' ', '')
    sanitized_file_content = file_content.replace('\n', '').replace(' ', '')

    return sanitized_expected in sanitized_file_content


def generate_test_notebook(work_dir: str, notebook_name: str):
    docstring = '"""\n' \
                ':param str subset: The kind of subset to generate.\n' \
                ':param int rate:\n' \
                '"""\n'
    cells = [

        '#Parameters\n{}subset = "train"\n'.format(docstring),

        'import numpy as np\n'
        'import pandas as pd\n'
        'from sklearn.datasets import fetch_20newsgroups\n',

        'newsgroups_train = fetch_20newsgroups(subset=subset,\n'
        '            remove=("headers", "footers", "quotes"))',

        '# Ignore\n'
        'df_train = pd.DataFrame(newsgroups_train.data, columns=["data"])',

        '# No effect\n'
        'df_train',

        'df_train.to_csv("data_train.csv", index=None)'
    ]
    notebook_path = gen_notebook(cells, work_dir, notebook_name)
    return cells, docstring, notebook_path


def test_should_generate_python_script_no_conf():
    """
        Convert a Jupyter Notebook to a Python 3 script using all parameters
    """
    with tempfile.TemporaryDirectory() as work_dir:
        cells, docstring, notebook_path = generate_test_notebook(work_dir=work_dir,
                                                                 notebook_name='test_nb.ipynb')

        output_path = join(work_dir, 'out.py')
        cmd_arguments = ['-n', notebook_path, '-o', output_path, '--working-directory', work_dir]
        IPynbToPython().run(*cmd_arguments)

        assert exists(output_path)

        with open(output_path, 'r') as fd:
            file_content = fd.read()

        assert 'def mlvtool_test_nb(subset: str, rate: int):' in file_content
        assert is_in(docstring, file_content)
        assert not is_in(cells[0], file_content)
        assert is_in(cells[1], file_content)
        assert is_in(cells[2], file_content)
        assert is_in(cells[3], file_content)
        assert not is_in(cells[4], file_content)
        assert is_in(cells[5], file_content)

        # Ensure generated file syntax is right
        compile(file_content, output_path, 'exec')


def test_should_generate_python_script_with_conf_auto_detect():
    """
        Convert a Jupyter Notebook to a Python 3 script using conf
    """
    with tempfile.TemporaryDirectory() as work_dir:
        subprocess.check_output(['git', 'init'], cwd=work_dir)
        cells, docstring, notebook_path = generate_test_notebook(work_dir=work_dir,
                                                                 notebook_name='test_nb.ipynb')
        # Create conf in a freshly init git repo
        conf_data = write_conf(work_dir=work_dir, conf_path=join(work_dir, DEFAULT_CONF_FILENAME),
                               ignore_keys=['# Ignore', 'remove='])

        cmd_arguments = ['-n', notebook_path]
        IPynbToPython().run(*cmd_arguments)

        # This path is generated using the conf script_dir and the notebook name
        output_script_path = join(work_dir, conf_data['path']['python_script_root_dir'], 'mlvtool_test_nb.py')
        assert exists(output_script_path)

        with open(output_script_path, 'r') as fd:
            file_content = fd.read()

        assert 'def mlvtool_test_nb(subset: str, rate: int):' in file_content
        assert is_in(docstring, file_content)
        assert not is_in(cells[0], file_content)
        assert is_in(cells[1], file_content)
        assert not is_in(cells[2], file_content)
        assert not is_in(cells[3], file_content)
        assert is_in(cells[4], file_content)
        assert is_in(cells[5], file_content)

        # Ensure generated file syntax is right
        compile(file_content, output_script_path, 'exec')


def test_should_raise_if_missing_output_path_argument_and_no_conf():
    """
        Test command raise if output path is not provided when no conf
    """
    arguments = ['-n', './test.ipynb', '--working-directory', './']
    with pytest.raises(MlVToolException):
        IPynbToPython().run(*arguments)


def test_should_raise_if_output_path_exist_and_no_force():
    """
        Test command raise if output path already exists and no force argument
    """
    with tempfile.TemporaryDirectory() as work_dir:
        output_path = join(work_dir, 'py_script')
        with open(output_path, 'w') as fd:
            fd.write('')
        arguments = ['-n', './test.ipynb', '--working-directory', work_dir, '-o', output_path]
        with pytest.raises(MlVToolException):
            IPynbToPython().run(*arguments)


def test_should_overwrite_with_force_argument():
    """
        Test output paths are overwritten with force argument
    """
    with tempfile.TemporaryDirectory() as work_dir:
        *_, notebook_path = generate_test_notebook(work_dir=work_dir,
                                                   notebook_name='test_nb.ipynb')
        output_path = join(work_dir, 'py_script')
        with open(output_path, 'w') as fd:
            fd.write('')
        arguments = ['-n', notebook_path, '--working-directory', work_dir, '-o', output_path,
                     '--force']
        IPynbToPython().run(*arguments)
        with open(output_path, 'r') as fd:
            assert fd.read()


def test_should_handle_notebook_with_invalid_python_name_with_conf():
    """
        Test invalid python filename are converted
    """
    with tempfile.TemporaryDirectory() as work_dir:
        subprocess.check_output(['git', 'init'], cwd=work_dir)
        cells, docstring, notebook_path = generate_test_notebook(work_dir=work_dir,
                                                                 notebook_name='01_(test) nb.ipynb')
        # Create conf in a freshly init git repo
        conf_data = write_conf(work_dir=work_dir, conf_path=join(work_dir, DEFAULT_CONF_FILENAME),
                               ignore_keys=['# Ignore', 'remove='])

        cmd_arguments = ['-n', notebook_path]
        IPynbToPython().run(*cmd_arguments)

        # This path is generated using the conf script_dir and the notebook name
        output_script_path = join(work_dir, conf_data['path']['python_script_root_dir'], 'mlvtool_01__test_nb.py')
        assert exists(output_script_path)

        with open(output_script_path, 'r') as fd:
            file_content = fd.read()

        # Ensure generated file syntax is right
        compile(file_content, output_script_path, 'exec')
