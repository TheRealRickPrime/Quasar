from quasar_win.editions import Edition, distribution
from test_ui_flow import window  # noqa: F401


def test_ads_only_live_on_secondary_surface_and_paid_suppresses(window):
    _app, win, _tmp = window
    licenses = win.ctx.licensing
    privacy = win.pages.widget(8)
    assert privacy.affiliates.isHidden()
    licenses.edition = Edition.FREE_ADS
    privacy.refresh()
    assert not privacy.affiliates.isHidden()
    from quasar_win.licensing import License
    licenses.license = License("pro", "synthetic@example.invalid", "test", "2026-01-01")
    privacy.refresh()
    assert privacy.affiliates.isHidden()
    assert win.pages.widget(1).findChild(type(privacy.affiliates), privacy.affiliates.objectName()) is not privacy.affiliates


def test_distribution_default_and_explicit_identity(tmp_path):
    assert distribution(tmp_path) is Edition.FREE
    (tmp_path / "distribution.json").write_text('{"edition":"pro"}')
    assert distribution(tmp_path) is Edition.PRO
