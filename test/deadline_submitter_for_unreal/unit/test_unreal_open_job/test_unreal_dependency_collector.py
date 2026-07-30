# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import MagicMock, patch

from deadline.client.job_bundle.submission import AssetReferences

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_dependency_collector import (  # noqa: E402
    DependencyCollector,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (  # noqa: E402
    RenderUnrealOpenJob,
    TransferProjectFilesStrategy,
    UnrealOpenJob,
)


def _make_mrq_job(*, ocio_enabled=True, ocio_asset_path="/Game/OCIO/Config.Config"):
    mrq_job = MagicMock()
    color_setting = MagicMock()
    color_setting.ocio_configuration.is_enabled = ocio_enabled
    configuration_source = color_setting.ocio_configuration.color_configuration.configuration_source
    configuration_source.get_path_name.return_value = ocio_asset_path
    mrq_job.get_configuration.return_value.find_setting_by_class.return_value = color_setting
    return mrq_job, configuration_source


def test_get_mrq_job_dependency_roots_includes_enabled_ocio_asset():
    mrq_job, _ = _make_mrq_job()

    with patch(
        "deadline.unreal_submitter.unreal_dependency_collector.common.soft_obj_path_to_str",
        side_effect=["/Game/Sequences/Main.Main", "/Game/Maps/Main.Main"],
    ):
        dependency_roots = DependencyCollector.get_mrq_job_dependency_roots(mrq_job)

    assert dependency_roots == [
        "/Game/Sequences/Main",
        "/Game/Maps/Main",
        "/Game/OCIO/Config",
    ]


def test_get_mrq_job_dependency_roots_ignores_disabled_ocio_setting():
    mrq_job, _ = _make_mrq_job(ocio_enabled=False)

    with patch(
        "deadline.unreal_submitter.unreal_dependency_collector.common.soft_obj_path_to_str",
        side_effect=["/Game/Sequences/Main.Main", "/Game/Maps/Main.Main"],
    ):
        dependency_roots = DependencyCollector.get_mrq_job_dependency_roots(mrq_job)

    assert dependency_roots == ["/Game/Sequences/Main", "/Game/Maps/Main"]


def test_get_mrq_job_dependency_roots_preserves_dots_in_directory_names():
    """Only the object suffix (after the LAST dot) is stripped; dots in
    directory names must survive. Regression test: partition('.') truncated
    '/Game/Ver1.2/Seq.Seq' to '/Game/Ver1'."""
    mrq_job, _ = _make_mrq_job(ocio_asset_path="/Game/My.Folder/Config.Config")

    with patch(
        "deadline.unreal_submitter.unreal_dependency_collector.common.soft_obj_path_to_str",
        side_effect=["/Game/Ver1.2/Seq.Seq", "/Game/My.Maps/Main.Main"],
    ):
        dependency_roots = DependencyCollector.get_mrq_job_dependency_roots(mrq_job)

    assert dependency_roots == [
        "/Game/Ver1.2/Seq",
        "/Game/My.Maps/Main",
        "/Game/My.Folder/Config",
    ]


def test_get_mrq_job_dependency_roots_skips_ocio_asset_outside_game_folder():
    """OCIO config assets outside /Game/ (e.g. plugin-mounted) are not collected."""
    mrq_job, _ = _make_mrq_job(ocio_asset_path="/OCIOPlugin/Config.Config")

    with patch(
        "deadline.unreal_submitter.unreal_dependency_collector.common.soft_obj_path_to_str",
        side_effect=["/Game/Sequences/Main.Main", "/Game/Maps/Main.Main"],
    ):
        dependency_roots = DependencyCollector.get_mrq_job_dependency_roots(mrq_job)

    assert dependency_roots == ["/Game/Sequences/Main", "/Game/Maps/Main"]


def test_get_mrq_job_ocio_config_file_path_skips_builtin_ocio_scheme():
    """Built-in configs referenced via the ocio:// scheme are not files on disk."""
    mrq_job, configuration_source = _make_mrq_job()
    configuration_source.configuration_file.file_path = "ocio://default"

    assert DependencyCollector.get_mrq_job_ocio_config_file_path(mrq_job) is None


def test_get_mrq_job_ocio_config_file_path_returns_none_for_empty_path():
    mrq_job, configuration_source = _make_mrq_job()
    configuration_source.configuration_file.file_path = ""

    assert DependencyCollector.get_mrq_job_ocio_config_file_path(mrq_job) is None


def test_get_mrq_job_ocio_config_file_path_returns_none_when_ocio_disabled():
    mrq_job, configuration_source = _make_mrq_job(ocio_enabled=False)
    configuration_source.configuration_file.file_path = "Content/OCIO/config.ocio"

    assert DependencyCollector.get_mrq_job_ocio_config_file_path(mrq_job) is None


def test_get_mrq_job_ocio_config_file_path_resolves_relative_path():
    mrq_job, configuration_source = _make_mrq_job()
    configuration_source.configuration_file.file_path = "Content/OCIO/config.ocio"

    with patch(
        "deadline.unreal_submitter.unreal_dependency_collector.common.os_abs_from_relative",
        return_value="C:\\Project\\Content\\OCIO\\config.ocio",
    ):
        config_path = DependencyCollector.get_mrq_job_ocio_config_file_path(mrq_job)

    assert config_path == "C:/Project/Content/OCIO/config.ocio"


def test_collect_mrq_job_dependencies_collects_each_dependency_root():
    render_job = RenderUnrealOpenJob.__new__(RenderUnrealOpenJob)
    render_job._mrq_job = MagicMock()  # type: ignore[assignment]
    render_job._dependency_collector = MagicMock()
    render_job._dependency_collector.get_mrq_job_dependency_roots.return_value = [
        "/Game/Sequences/Main",
        "/Game/Maps/Main",
        "/Game/OCIO/Config",
    ]
    render_job._dependency_collector.collect.side_effect = [
        ["/Game/Sequences/Shot"],
        ["/Game/Maps/Material"],
        ["/Game/OCIO/Lut"],
    ]

    dependencies = render_job._collect_mrq_job_dependencies()

    assert set(dependencies) == {
        "/Game/Sequences/Main",
        "/Game/Sequences/Shot",
        "/Game/Maps/Main",
        "/Game/Maps/Material",
        "/Game/OCIO/Config",
        "/Game/OCIO/Lut",
    }
    assert render_job._dependency_collector.collect.call_count == 3


def test_get_asset_references_includes_external_ocio_config_file():
    render_job = RenderUnrealOpenJob.__new__(RenderUnrealOpenJob)
    render_job._mrq_job = MagicMock()  # type: ignore[assignment]
    render_job._transfer_files_strategy = TransferProjectFilesStrategy.P4
    render_job._dependency_collector = MagicMock()
    render_job._dependency_collector.get_mrq_job_ocio_config_file_path.return_value = (
        "C:/Project/Content/OCIO/config.ocio"
    )
    render_job._extra_parameters = []

    with (
        patch.object(UnrealOpenJob, "get_asset_references", return_value=AssetReferences()),
        patch.object(render_job, "_get_mrq_job_attachments_input_files", return_value=[]),
        patch.object(render_job, "_get_mrq_job_attachments_input_directories", return_value=[]),
        patch.object(render_job, "_get_mrq_job_attachments_output_directories", return_value=[]),
        patch.object(
            render_job, "_get_mrq_job_output_directory", return_value="C:/Project/Renders"
        ),
        patch(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.os.path.exists",
            return_value=True,
        ),
    ):
        asset_references = render_job.get_asset_references()

    assert "C:/Project/Content/OCIO/config.ocio" in asset_references.input_filenames


def test_get_asset_references_skips_missing_ocio_config_file():
    """A referenced-but-missing OCIO config file is warned about, not attached."""
    render_job = RenderUnrealOpenJob.__new__(RenderUnrealOpenJob)
    render_job._mrq_job = MagicMock()  # type: ignore[assignment]
    render_job._transfer_files_strategy = TransferProjectFilesStrategy.P4
    render_job._dependency_collector = MagicMock()
    render_job._dependency_collector.get_mrq_job_ocio_config_file_path.return_value = (
        "C:/Project/Content/OCIO/missing.ocio"
    )
    render_job._extra_parameters = []

    with (
        patch.object(UnrealOpenJob, "get_asset_references", return_value=AssetReferences()),
        patch.object(render_job, "_get_mrq_job_attachments_input_files", return_value=[]),
        patch.object(render_job, "_get_mrq_job_attachments_input_directories", return_value=[]),
        patch.object(render_job, "_get_mrq_job_attachments_output_directories", return_value=[]),
        patch.object(
            render_job, "_get_mrq_job_output_directory", return_value="C:/Project/Renders"
        ),
        patch(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.os.path.exists",
            return_value=False,
        ),
    ):
        asset_references = render_job.get_asset_references()

    assert "C:/Project/Content/OCIO/missing.ocio" not in asset_references.input_filenames
