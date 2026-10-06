"""Exercise the local HPC plan checker; never connects to Slurm or a GPU."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / '.agents/skills/run-carla-uit-hpc/scripts/check_plan.py'


def checker():
    assert CHECKER.is_file(), 'Missing HPC safety checker; current setup cannot reject unsafe plans'
    spec = importlib.util.spec_from_file_location('hpc_check_plan', CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plan(**changes):
    # Hand-checked normal partition fixture from source document section5.2.
    data = dict(operation='gpu_workload', node_kind='compute', slurm_job_id='12345',
                username='researcher', account='uit', partition='normal', gres='gpu:2g.35gb:1',
                cpus=4, memory_gb=4, time_hours=1, queued_jobs=0,
                workdir='/datastore/researcher/project', home_usage_gb=1, gpu_mode='mig')
    data.update(changes)
    return data


def test_normal_gpu_training_in_allocated_job_allowed():
    result = checker().validate(plan())
    assert result == {'allowed': True, 'reasons': []}


@pytest.mark.parametrize('partition,gres,cpus,ram', [
    ('small', 'gpu:1g.18gb:1', 12, 40),
    ('normal', 'gpu:2g.35gb:1', 16, 72),
    ('large', 'gpu:3g.71gb:1', 24, 112),
])
def test_carla_renderer_blocked_on_every_documented_mig_profile(partition, gres, cpus, ram):
    result = checker().validate(plan(operation='carla_server', partition=partition, gres=gres,
                                     cpus=cpus, memory_gb=ram))
    assert result['allowed'] is False
    assert 'MIG_RENDERER_UNSUPPORTED' in result['reasons']


@pytest.mark.parametrize('changes,reason', [
    ({'node_kind': 'login'}, 'LOGIN_COMPUTE_FORBIDDEN'),
    ({'slurm_job_id': None}, 'SLURM_ALLOCATION_REQUIRED'),
    ({'account': 'root'}, 'ACCOUNT_NOT_DOCUMENTED'),
    ({'partition': 'full-h200'}, 'PARTITION_NOT_DOCUMENTED'),
    ({'gres': 'gpu:3g.71gb:1'}, 'GRES_PARTITION_MISMATCH'),
    ({'cpus': 17}, 'CPU_LIMIT_EXCEEDED'),
    ({'memory_gb': 73}, 'RAM_LIMIT_EXCEEDED'),
    ({'time_hours': 73}, 'TIME_LIMIT_EXCEEDED'),
    ({'home_usage_gb': 12}, 'HOME_CONSERVATIVE_LIMIT_EXCEEDED'),
    ({'workdir': '/home/researcher/carla'}, 'DATASTORE_REQUIRED'),
    ({'workdir': '/shared/results'}, 'READ_ONLY_STORAGE'),
    ({'workdir': '/h200node01/results'}, 'READ_ONLY_STORAGE'),
    ({'workdir': '/datastore/researcher/../../shared/results'}, 'DATASTORE_REQUIRED'),
    ({'operation': 'offline_analysis'}, 'CPU_ONLY_SCOPE_NOT_AUTHORIZED'),
    ({'cpus': True}, 'INVALID_RESOURCE_VALUE'),
    ({'time_hours': 0}, 'INVALID_RESOURCE_VALUE'),
])
def test_unsafe_plan_rejected(changes, reason):
    result = checker().validate(plan(**changes))
    assert not result['allowed']
    assert reason in result['reasons']


def test_submission_blocks_51st_queued_job_but_allows_50th():
    module = checker()
    assert module.validate(plan(operation='submit_gpu_job', node_kind='login', slurm_job_id=None,
                                queued_jobs=49))['allowed']
    result = module.validate(plan(operation='submit_gpu_job', node_kind='login', slurm_job_id=None,
                                  queued_jobs=50))
    assert not result['allowed']
    assert 'QUEUE_LIMIT_EXCEEDED' in result['reasons']


def test_missing_evidence_and_malformed_input_fail_closed():
    module = checker()
    for data in [{}, {'operation': 'gpu_workload'}, None, [], 'run now']:
        assert module.validate(data)['allowed'] is False


def test_large_vram_and_offscreen_do_not_bypass_mig():
    result = checker().validate(plan(operation='carla_server', partition='large',
        gres='gpu:3g.71gb:1', cpus=24, memory_gb=112, render_offscreen=True, no_rendering=True))
    assert not result['allowed']
    assert 'MIG_RENDERER_UNSUPPORTED' in result['reasons']


def test_claiming_full_gpu_on_mig_partition_does_not_override_policy():
    result = checker().validate(plan(operation='carla_server', gpu_mode='full',
                                     admin_approved=True, disable_mig=True))
    assert not result['allowed']
    assert 'MIG_RENDERER_UNSUPPORTED' in result['reasons']


def test_cli_exit_and_json_are_machine_readable(tmp_path):
    checker()
    p = tmp_path / 'plan.json'
    p.write_text(json.dumps(plan(operation='carla_server')))
    result = subprocess.run([sys.executable, str(CHECKER), str(p)], capture_output=True,
                            text=True, timeout=5)
    assert result.returncode == 2
    assert json.loads(result.stdout)['allowed'] is False
    p.write_text(json.dumps(plan()))
    result = subprocess.run([sys.executable, str(CHECKER), str(p)], capture_output=True,
                            text=True, timeout=5)
    assert result.returncode == 0
    assert json.loads(result.stdout)['allowed'] is True


@pytest.mark.parametrize('field', ['operation', 'node_kind', 'account', 'partition', 'gres', 'gpu_mode', 'username', 'workdir'])
def test_wrong_json_field_types_fail_closed(field):
    module = checker()
    for value in [None, [], {}, True]:
        assert module.validate(plan(**{field: value}))['allowed'] is False


def test_extremely_large_resource_requests_rejected_without_overflow():
    module = checker()
    for field in ['cpus', 'memory_gb', 'time_hours', 'home_usage_gb']:
        result = module.validate(plan(**{field: 10 ** 400}))
        assert not result['allowed']


def test_missing_or_malformed_policy_blocks(tmp_path):
    module = checker()
    module.POLICY = tmp_path / 'policy.json'
    assert not module.validate(plan())['allowed']
    for text in ['{invalid', '[]', '{}']:
        module.POLICY.write_text(text)
        assert not module.validate(plan())['allowed']


def test_cli_invalid_json_blocks_without_traceback(tmp_path):
    checker()
    p = tmp_path / 'bad.json'
    p.write_text('{invalid')
    result = subprocess.run([sys.executable, str(CHECKER), str(p)], capture_output=True,
                            text=True, timeout=5)
    assert result.returncode == 2
    assert not json.loads(result.stdout)['allowed']
    assert 'Traceback' not in result.stderr
