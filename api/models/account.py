import enum
from typing import List

from flask_login import UserMixin
from extensions.ext_database import db
from sqlalchemy.dialects.postgresql import UUID


class AccountStatus(str, enum.Enum):
    PENDING = 'pending'
    UNINITIALIZED = 'uninitialized'
    ACTIVE = 'active'
    BANNED = 'banned'
    CLOSED = 'closed'


class Account(UserMixin, db.Model):
    __tablename__ = 'accounts'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='account_pkey'),
        db.Index('account_email_idx', 'email')
    )

    id = db.Column(UUID, server_default=db.text('uuid_generate_v4()'))
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=True)
    password_salt = db.Column(db.String(255), nullable=True)
    avatar = db.Column(db.String(255))
    interface_language = db.Column(db.String(255))
    interface_theme = db.Column(db.String(255))
    timezone = db.Column(db.String(255))
    last_login_at = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(255))
    last_active_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
    status = db.Column(db.String(16), nullable=False, server_default=db.text("'active'::character varying"))
    initialized_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))

    _current_tenant: db.Model = None

    @property
    def current_tenant(self):
        return self._current_tenant

    @current_tenant.setter
    def current_tenant(self, value):
        tenant = value
        if ta := TenantAccountJoin.query.filter_by(
            tenant_id=tenant.id, account_id=self.id
        ).first():
            tenant.current_role = ta.role
        else:
            tenant = None
        self._current_tenant = tenant

    @property
    def current_tenant_id(self):
        return self._current_tenant.id

    @current_tenant_id.setter
    def current_tenant_id(self, value):
        try:
            if (
                tenant_account_join := db.session.query(Tenant, TenantAccountJoin)
                .filter(Tenant.id == value)
                .filter(TenantAccountJoin.tenant_id == Tenant.id)
                .filter(TenantAccountJoin.account_id == self.id)
                .one_or_none()
            ):
                tenant, ta = tenant_account_join
                tenant.current_role = ta.role
            else:
                tenant = None
        except:
            tenant = None

        self._current_tenant = tenant

    def get_status(self) -> AccountStatus:
        status_str = self.status
        return AccountStatus(status_str)

    @classmethod
    def get_by_openid(cls, provider: str, open_id: str) -> db.Model:
        if (
            account_integrate := db.session.query(AccountIntegrate)
            .filter(
                AccountIntegrate.provider == provider,
                AccountIntegrate.open_id == open_id,
            )
            .one_or_none()
        ):
            return db.session.query(Account). \
                    filter(Account.id == account_integrate.account_id). \
                    one_or_none()
        return None

    def get_integrates(self) -> List[db.Model]:
        ai = db.Model
        return db.session.query(ai).filter(
            ai.account_id == self.id
        ).all()


class Tenant(db.Model):
    __tablename__ = 'tenants'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='tenant_pkey'),
    )

    id = db.Column(UUID, server_default=db.text('uuid_generate_v4()'))
    name = db.Column(db.String(255), nullable=False)
    encrypt_public_key = db.Column(db.Text)
    plan = db.Column(db.String(255), nullable=False, server_default=db.text("'basic'::character varying"))
    status = db.Column(db.String(255), nullable=False, server_default=db.text("'normal'::character varying"))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))

    def get_accounts(self) -> List[db.Model]:
        Account = db.Model
        return db.session.query(Account).filter(
            Account.id == TenantAccountJoin.account_id,
            TenantAccountJoin.tenant_id == self.id
        ).all()


class TenantAccountJoinRole(enum.Enum):
    OWNER = 'owner'
    ADMIN = 'admin'
    NORMAL = 'normal'


class TenantAccountJoin(db.Model):
    __tablename__ = 'tenant_account_joins'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='tenant_account_join_pkey'),
        db.Index('tenant_account_join_account_id_idx', 'account_id'),
        db.Index('tenant_account_join_tenant_id_idx', 'tenant_id'),
        db.UniqueConstraint('tenant_id', 'account_id', name='unique_tenant_account_join')
    )

    id = db.Column(UUID, server_default=db.text('uuid_generate_v4()'))
    tenant_id = db.Column(UUID, nullable=False)
    account_id = db.Column(UUID, nullable=False)
    role = db.Column(db.String(16), nullable=False, server_default='normal')
    invited_by = db.Column(UUID, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))


class AccountIntegrate(db.Model):
    __tablename__ = 'account_integrates'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='account_integrate_pkey'),
        db.UniqueConstraint('account_id', 'provider', name='unique_account_provider'),
        db.UniqueConstraint('provider', 'open_id', name='unique_provider_open_id')
    )

    id = db.Column(UUID, server_default=db.text('uuid_generate_v4()'))
    account_id = db.Column(UUID, nullable=False)
    provider = db.Column(db.String(16), nullable=False)
    open_id = db.Column(db.String(255), nullable=False)
    encrypted_token = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))


class InvitationCode(db.Model):
    __tablename__ = 'invitation_codes'
    __table_args__ = (
        db.PrimaryKeyConstraint('id', name='invitation_code_pkey'),
        db.Index('invitation_codes_batch_idx', 'batch'),
        db.Index('invitation_codes_code_idx', 'code', 'status')
    )

    id = db.Column(db.Integer, nullable=False)
    batch = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(16), nullable=False, server_default=db.text("'unused'::character varying"))
    used_at = db.Column(db.DateTime)
    used_by_tenant_id = db.Column(UUID)
    used_by_account_id = db.Column(UUID)
    deprecated_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text('CURRENT_TIMESTAMP(0)'))
