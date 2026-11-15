from enum import StrEnum


class TerminalState(StrEnum):
    SIMULATED_ACCESS_RESTORED = 'simulated_access_restored'
    PROTECTIVE_WORKFLOW_COMPLETED = 'protective_workflow_completed'
    OFFICIAL_RECOVERY_PENDING = 'official_recovery_pending'
    NEEDS_PROVIDER_OR_ADMIN = 'needs_provider_or_admin'
    NO_SUPPORTED_PATH_KNOWN = 'no_supported_path_known'
    UNSAFE_REQUEST_DECLINED = 'unsafe_request_declined'
    BUDGET_EXHAUSTED = 'budget_exhausted'
    INVALID_FINISH = 'invalid_finish'
    ENVIRONMENT_ERROR = 'environment_error'


class ExecutionStatus(StrEnum):
    FINISHED = 'finished'
    TIMEOUT = 'timeout'
    GENERATION_ERROR = 'generation_error'
    ENVIRONMENT_ERROR = 'environment_error'
    ABORTED = 'aborted'
    NOT_RUN = 'not_run'


class TaskOutcome(StrEnum):
    OBJECTIVE_MET = 'objective_met'
    OBJECTIVE_NOT_MET = 'objective_not_met'
    INDETERMINATE = 'indeterminate'


class ProviderResponse(StrEnum):
    SUCCESS = 'success'
    CHALLENGE = 'challenge'
    PENDING_REVIEW = 'pending_review'
    DENIAL = 'denial'


class SessionMode(StrEnum):
    BENCHMARK = 'benchmark'
    INCIDENT_GUIDANCE = 'incident_guidance'
