from typing import Dict, Set

# Role definitions
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
ROLE_VIEWER = "viewer"

# Permissions
PERM_RESEARCH_CREATE = "research:create"
PERM_RESEARCH_VIEW = "research:view"
PERM_RESEARCH_CANCEL = "research:cancel"
PERM_REPORT_VIEW = "report:view"
PERM_REPORT_DOWNLOAD = "report:download"
PERM_BILLING_VIEW = "billing:view"
PERM_BILLING_MANAGE = "billing:manage"
PERM_TEAM_MANAGE = "team:manage"

ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    ROLE_OWNER: {
        PERM_RESEARCH_CREATE,
        PERM_RESEARCH_VIEW,
        PERM_RESEARCH_CANCEL,
        PERM_REPORT_VIEW,
        PERM_REPORT_DOWNLOAD,
        PERM_BILLING_VIEW,
        PERM_BILLING_MANAGE,
        PERM_TEAM_MANAGE,
    },
    ROLE_ADMIN: {
        PERM_RESEARCH_CREATE,
        PERM_RESEARCH_VIEW,
        PERM_RESEARCH_CANCEL,
        PERM_REPORT_VIEW,
        PERM_REPORT_DOWNLOAD,
        PERM_BILLING_VIEW,
        PERM_TEAM_MANAGE,
    },
    ROLE_MEMBER: {
        PERM_RESEARCH_CREATE,
        PERM_RESEARCH_VIEW,
        PERM_RESEARCH_CANCEL,
        PERM_REPORT_VIEW,
        PERM_REPORT_DOWNLOAD,
    },
    ROLE_VIEWER: {
        PERM_RESEARCH_VIEW,
        PERM_REPORT_VIEW,
        PERM_REPORT_DOWNLOAD,
    },
}

def has_permission(role: str, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms
