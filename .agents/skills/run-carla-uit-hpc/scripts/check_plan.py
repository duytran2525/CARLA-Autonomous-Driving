#!/usr/bin/env python3
"""Read-only proposal checker, not a scheduler, credential handler or execution sandbox.

JSON metadata is declarative, not live proof. A pass is necessary but insufficient:
read the policy and verify actual Slurm allocation, mounts and quotas before execution.
No network, subprocess, GPU probe, file deletion or job submission occurs here.
"""
import argparse
import json
import math
from pathlib import Path
import posixpath
import re

POLICY = Path(__file__).resolve().parents[1] / 'references/policy.json'


def validate(plan):
    if not isinstance(plan, dict):
        return {'allowed': False, 'reasons': ['INVALID_PLAN']}
    try:
        policy = json.loads(POLICY.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'allowed': False, 'reasons': ['POLICY_UNAVAILABLE']}
    # Reject malformed local policy at the JSON boundary, before any indexing/arithmetic.
    try:
        if policy['schema_version'] != 1 or not isinstance(policy['account'], str):
            raise ValueError('invalid schema/account')
        for field in ['time_hours_max', 'queued_jobs_max', 'home_conservative_gb_max']:
            if type(policy[field]) is not int or policy[field] <= 0:
                raise ValueError('invalid policy ceiling')
        if not isinstance(policy['read_only_roots'], list) or not all(
                isinstance(x, str) and x.startswith('/') for x in policy['read_only_roots']):
            raise ValueError('invalid storage policy')
        profiles = policy['profiles']
        if not isinstance(profiles, dict) or not profiles:
            raise ValueError('missing profiles')
        for profile in profiles.values():
            if not isinstance(profile['gres'], str) or profile['gpu_mode'] not in ('mig', 'full'):
                raise ValueError('invalid GPU policy')
            for field in ['cpu_max', 'ram_gb_max']:
                if type(profile[field]) is not int or profile[field] <= 0:
                    raise ValueError('invalid profile ceiling')
    except (KeyError, TypeError, ValueError):
        return {'allowed': False, 'reasons': ['INVALID_POLICY']}
    reasons = []
    required = {'operation', 'node_kind', 'slurm_job_id', 'username', 'account',
                'partition', 'gres', 'cpus', 'memory_gb', 'time_hours', 'queued_jobs',
                'workdir', 'home_usage_gb', 'gpu_mode'}
    if not required.issubset(plan):
        return {'allowed': False, 'reasons': ['MISSING_EVIDENCE']}
    string_fields = ['operation', 'node_kind', 'username', 'account', 'partition',
                     'gres', 'workdir', 'gpu_mode']
    if not all(isinstance(plan[field], str) for field in string_fields):
        return {'allowed': False, 'reasons': ['INVALID_PLAN_FIELD_TYPE']}
    op = plan['operation']
    if op == 'offline_analysis':
        reasons.append('CPU_ONLY_SCOPE_NOT_AUTHORIZED')
    elif op not in {'carla_server', 'gpu_workload', 'submit_gpu_job'}:
        reasons.append('OPERATION_NOT_AUTHORIZED')
    submitting = op == 'submit_gpu_job'
    if not submitting:
        if plan['node_kind'] == 'login':
            reasons.append('LOGIN_COMPUTE_FORBIDDEN')
        elif plan['node_kind'] != 'compute':
            reasons.append('COMPUTE_NODE_REQUIRED')
        job_id = plan['slurm_job_id']
        if not isinstance(job_id, (str, int)) or isinstance(job_id, bool) or not re.fullmatch(r'[1-9][0-9]*(?:_[0-9]+)?', str(job_id)):
            reasons.append('SLURM_ALLOCATION_REQUIRED')
    if plan['account'] != policy['account']:
        reasons.append('ACCOUNT_NOT_DOCUMENTED')
    partition = plan['partition']
    profile = policy['profiles'].get(partition) if isinstance(partition, str) else None
    if profile is None:
        reasons.append('PARTITION_NOT_DOCUMENTED')
    else:
        if plan['gres'] != profile['gres']:
            reasons.append('GRES_PARTITION_MISMATCH')
        # Trust the documented resource, not a supplied 'full GPU/admin_approved' flag.
        if op == 'carla_server' and profile['gpu_mode'] == 'mig':
            reasons.append('MIG_RENDERER_UNSUPPORTED')
        if plan['gpu_mode'] != profile['gpu_mode']:
            reasons.append('GPU_MODE_POLICY_MISMATCH')
    limits = {'cpus': ('cpu_max', 'CPU_LIMIT_EXCEEDED'),
              'memory_gb': ('ram_gb_max', 'RAM_LIMIT_EXCEEDED')}
    for field, (limit, reason) in limits.items():
        value = plan[field]
        valid = (type(value) is int if field == 'cpus' else type(value) in (int, float))
        if not valid or (type(value) is float and not math.isfinite(value)) or value <= 0:
            reasons.append('INVALID_RESOURCE_VALUE')
        elif profile and value > profile[limit]:
            reasons.append(reason)
    hours = plan['time_hours']
    if type(hours) not in (int, float) or (type(hours) is float and not math.isfinite(hours)) or hours <= 0:
        reasons.append('INVALID_RESOURCE_VALUE')
    elif hours > policy['time_hours_max']:
        reasons.append('TIME_LIMIT_EXCEEDED')
    queued = plan['queued_jobs']
    if type(queued) is not int or queued < 0:
        reasons.append('QUEUE_EVIDENCE_REQUIRED')
    elif queued > policy['queued_jobs_max'] or (submitting and queued >= policy['queued_jobs_max']):
        reasons.append('QUEUE_LIMIT_EXCEEDED')
    home = plan['home_usage_gb']
    if type(home) not in (int, float) or (type(home) is float and not math.isfinite(home)) or home < 0:
        reasons.append('HOME_QUOTA_EVIDENCE_REQUIRED')
    elif home > policy['home_conservative_gb_max']:
        reasons.append('HOME_CONSERVATIVE_LIMIT_EXCEEDED')
    username, workdir = plan['username'], plan['workdir']
    if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', username):
        reasons.append('INVALID_USERNAME')
    elif not isinstance(workdir, str) or not workdir.startswith('/') or '\x00' in workdir:
        reasons.append('DATASTORE_REQUIRED')
    else:
        directory = posixpath.normpath(workdir)
        base = '/datastore/' + username
        if directory != base and not directory.startswith(base + '/'):
            reasons.append('DATASTORE_REQUIRED')
        if any(directory == x or directory.startswith(x + '/') for x in policy['read_only_roots']):
            reasons.append('READ_ONLY_STORAGE')
    return {'allowed': not reasons, 'reasons': list(dict.fromkeys(reasons))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path, help='JSON proposal; does not submit or execute it')
    args = parser.parse_args()
    try:
        data = json.loads(args.plan.read_text(encoding='utf-8'))
        result = validate(data)
    except (OSError, ValueError) as exc:
        result = {'allowed': False, 'reasons': ['UNREADABLE_OR_INVALID_PLAN'], 'detail': str(exc)}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['allowed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
