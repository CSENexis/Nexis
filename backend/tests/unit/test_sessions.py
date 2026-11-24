import uuid
from datetime import datetime, timezone, timedelta
from app.db.models import User, SessionModel, SessionState
from app.modules.sessions.service import (
    create_session,
    validate_and_refresh_session,
    rotate_session,
    revoke_session,
    revoke_all_user_sessions
)

def test_session_creation_and_validation(db_session):
    user_id = uuid.uuid4()
    raw_token, session_record = create_session(db_session, user_id, SessionState.AUTHENTICATED)

    assert raw_token is not None
    assert session_record.id is not None
    assert session_record.user_id == user_id
    assert session_record.state == SessionState.AUTHENTICATED

    # Validate active session
    validated = validate_and_refresh_session(db_session, raw_token)
    assert validated is not None
    assert validated.user_id == user_id


def test_session_idle_timeout(db_session):
    user_id = uuid.uuid4()
    raw_token, session_record = create_session(db_session, user_id, SessionState.AUTHENTICATED)

    # Fast forward idle_expires_at to the past
    session_record.idle_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    # Should be rejected due to idle expiration
    validated = validate_and_refresh_session(db_session, raw_token)
    assert validated is None

    # Should be marked REVOKED in DB
    db_session.refresh(session_record)
    assert session_record.state == SessionState.REVOKED


def test_session_absolute_timeout(db_session):
    user_id = uuid.uuid4()
    raw_token, session_record = create_session(db_session, user_id, SessionState.AUTHENTICATED)

    # Fast forward absolute_expires_at to the past
    session_record.absolute_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    validated = validate_and_refresh_session(db_session, raw_token)
    assert validated is None
    db_session.refresh(session_record)
    assert session_record.state == SessionState.REVOKED


def test_session_rotation(db_session):
    user_id = uuid.uuid4()
    raw_token_old, session_old = create_session(db_session, user_id, SessionState.MFA_PENDING)

    # Rotate session to AUTHENTICATED
    raw_token_new, session_new = rotate_session(
        db_session,
        old_token_hash=session_old.id,
        user_id=user_id,
        new_state=SessionState.AUTHENTICATED
    )

    assert raw_token_new != raw_token_old
    assert session_new.id != session_old.id
    assert session_new.state == SessionState.AUTHENTICATED

    # Old session must now be revoked
    db_session.refresh(session_old)
    assert session_old.state == SessionState.REVOKED


def test_revoke_all_user_sessions(db_session):
    user_id = uuid.uuid4()
    _, s1 = create_session(db_session, user_id, SessionState.AUTHENTICATED)
    _, s2 = create_session(db_session, user_id, SessionState.AUTHENTICATED)

    revoked_count = revoke_all_user_sessions(db_session, user_id)
    assert revoked_count == 2

    db_session.refresh(s1)
    db_session.refresh(s2)
    assert s1.state == SessionState.REVOKED
    assert s2.state == SessionState.REVOKED
