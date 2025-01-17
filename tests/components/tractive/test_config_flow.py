"""Test the tractive config flow."""
from unittest.mock import patch

import aiotractive

from homeassistant import config_entries, setup
from homeassistant.components.tractive.const import DOMAIN
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

USER_INPUT = {
    "email": "test-email@example.com",
    "password": "test-password",
}


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] is None

    with patch(
        "aiotractive.api.API.user_id", return_value={"user_id": "user_id"}
    ), patch(
        "homeassistant.components.tractive.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "test-email@example.com"
    assert result2["data"] == USER_INPUT
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "aiotractive.api.API.user_id",
        side_effect=aiotractive.exceptions.UnauthorizedError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_unknown_error(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "aiotractive.api.API.user_id",
        side_effect=Exception,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "unknown"}


async def test_flow_entry_already_exists(hass: HomeAssistant) -> None:
    """Test user input for config_entry that already exists."""
    first_entry = MockConfigEntry(
        domain="tractive",
        data=USER_INPUT,
        unique_id="USERID",
    )
    first_entry.add_to_hass(hass)

    with patch("aiotractive.api.API.user_id", return_value="USERID"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=USER_INPUT
        )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


async def test_reauthentication(hass):
    """Test Tractive reauthentication."""
    old_entry = MockConfigEntry(
        domain="tractive",
        data=USER_INPUT,
        unique_id="USERID",
    )
    old_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "unique_id": old_entry.unique_id,
            "entry_id": old_entry.entry_id,
        },
        data=old_entry.data,
    )

    assert result["type"] == "form"
    assert result["errors"] == {}
    assert result["step_id"] == "reauth_confirm"

    with patch("aiotractive.api.API.user_id", return_value="USERID"), patch(
        "homeassistant.components.tractive.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result2["type"] == "abort"
    assert result2["reason"] == "reauth_successful"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_reauthentication_failure(hass):
    """Test Tractive reauthentication failure."""
    old_entry = MockConfigEntry(
        domain="tractive",
        data=USER_INPUT,
        unique_id="USERID",
    )
    old_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "unique_id": old_entry.unique_id,
            "entry_id": old_entry.entry_id,
        },
        data=old_entry.data,
    )

    assert result["type"] == "form"
    assert result["errors"] == {}
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "aiotractive.api.API.user_id",
        side_effect=aiotractive.exceptions.UnauthorizedError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result2["step_id"] == "reauth_confirm"
    assert result["type"] == "form"
    assert result2["errors"]["base"] == "invalid_auth"


async def test_reauthentication_unknown_failure(hass):
    """Test Tractive reauthentication failure."""
    old_entry = MockConfigEntry(
        domain="tractive",
        data=USER_INPUT,
        unique_id="USERID",
    )
    old_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "unique_id": old_entry.unique_id,
            "entry_id": old_entry.entry_id,
        },
        data=old_entry.data,
    )

    assert result["type"] == "form"
    assert result["errors"] == {}
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "aiotractive.api.API.user_id",
        side_effect=Exception,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result2["step_id"] == "reauth_confirm"
    assert result["type"] == "form"
    assert result2["errors"]["base"] == "unknown"


async def test_reauthentication_failure_no_existing_entry(hass):
    """Test Tractive reauthentication with no existing entry."""
    old_entry = MockConfigEntry(
        domain="tractive",
        data=USER_INPUT,
        unique_id="USERID",
    )
    old_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "unique_id": old_entry.unique_id,
            "entry_id": old_entry.entry_id,
        },
        data=old_entry.data,
    )

    assert result["type"] == "form"
    assert result["errors"] == {}
    assert result["step_id"] == "reauth_confirm"

    with patch("aiotractive.api.API.user_id", return_value="USERID_DIFFERENT"):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
        await hass.async_block_till_done()

    assert result2["type"] == "abort"
    assert result2["reason"] == "reauth_failed_existing"
