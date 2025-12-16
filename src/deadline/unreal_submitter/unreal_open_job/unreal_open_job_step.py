# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import math
import unreal
from enum import IntEnum
from typing import Optional, Any
from dataclasses import dataclass, field, asdict

from openjd.model import parse_model
from openjd.model.v2023_09 import (
    StepScript,
    StepTemplate,
    TaskParameterType,
    HostRequirementsTemplate,
    TaskParameterList,
    StepParameterSpaceDefinition,
)


from openjd.model.v2023_09._model import StepDependency

from deadline.unreal_submitter import common
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (
    UnrealOpenJobEntity,
    OpenJobStepParameterNames,
    PARAMETER_DEFINITION_MAPPING,
    ParameterDefinitionDescriptor,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (
    UnrealOpenJobEnvironment,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_parameters_consistency import (
    ParametersConsistencyChecker,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_chunk import (
    ChunkConfiguration,
    ChunkIntTaskParameter,
    RangeConstraint,
)
from deadline.unreal_logger import get_logger
from deadline.unreal_submitter import exceptions, settings
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step_host_requirements import (
    HostRequirementsHelper,
)

logger = get_logger()


@dataclass
class UnrealOpenJobStepParameterDefinition:
    """
    Dataclass for storing and managing OpenJob Step Task parameter definitions

    :cvar name: Name of the parameter
    :cvar type: OpenJD Type of the parameter (INT, FLOAT, STRING, PATH)
    :cvar range: List of parameter values
    :cvar chunks: Optional chunk configuration for CHUNK[INT] parameters
    """

    name: str
    type: str
    range: list[Any] = field(default_factory=list)
    chunks: Optional[dict] = None

    @classmethod
    def from_unreal_param_definition(cls, u_param: unreal.StepTaskParameterDefinition):
        """
        Create UnrealOpenJobStepParameterDefinition instance from unreal.StepTaskParameterDefinition
        object.

        :return: UnrealOpenJobStepParameterDefinition instance
        :rtype: UnrealOpenJobStepParameterDefinition
        """

        python_class = PARAMETER_DEFINITION_MAPPING[u_param.type.name].python_class
        build_kwargs = dict(
            name=u_param.name,
            type=u_param.type.name,
            range=[python_class(p) for p in list(u_param.range)],
        )
        return cls(**build_kwargs)

    @classmethod
    def from_dict(cls, param_dict: dict):
        """
        Create UnrealOpenJobStepParameterDefinition instance python dict

        :return: UnrealOpenJobStepParameterDefinition instance
        :rtype: UnrealOpenJobStepParameterDefinition
        """

        return cls(**param_dict)

    def to_dict(self):
        """
        Return UnrealOpenJobStepParameterDefinition as dictionary

        :return: UnrealOpenJobStepParameterDefinition as python dictionary
        :rtype: dict[str, Any]
        """

        return asdict(self)


# Base Step implementation
class UnrealOpenJobStep(UnrealOpenJobEntity):
    """
    Unreal Open Job Step entity
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        name: Optional[str] = None,
        step_dependencies: Optional[list[str]] = None,
        environments: Optional[list[UnrealOpenJobEnvironment]] = None,
        extra_parameters: Optional[list[UnrealOpenJobStepParameterDefinition]] = None,
        host_requirements: Optional[HostRequirementsTemplate] = None,
    ):
        """
        :param file_path: The file path of the step descriptor
        :type file_path: str

        :param name: The name of the step
        :type name: str

        :param step_dependencies: The list of step dependencies
        :type step_dependencies: list[str]

        :param environments: The list of environments
        :type environments: list[UnrealOpenJobEnvironment]

        :param extra_parameters: Extra Step parameters that should be used during the Job execution
        :type extra_parameters: list[UnrealOpenJobStepParameterDefinition]

        :param host_requirements: HostRequirements to apply to step during the Job execution
        :type host_requirements: HostRequirements
        """

        self._step_dependencies = step_dependencies or []

        self._environments = environments or []

        self._extra_parameters = extra_parameters or []

        self._host_requirements = host_requirements

        super().__init__(StepTemplate, file_path, name)

        self._create_missing_extra_parameters_from_template()

        self._open_job = None

    @property
    def host_requirements(self):
        return self._host_requirements

    @host_requirements.setter
    def host_requirements(self, value: Optional[HostRequirementsTemplate]):
        self._host_requirements = value

    @property
    def step_dependencies(self) -> list[str]:
        return self._step_dependencies

    @step_dependencies.setter
    def step_dependencies(self, value: list[str]):
        self._step_dependencies = value

    @property
    def environments(self) -> list[UnrealOpenJobEnvironment]:
        return self._environments

    @environments.setter
    def environments(self, value: list[UnrealOpenJobEnvironment]):
        self._environments = value

    @property
    def open_job(self):
        return self._open_job

    @open_job.setter
    def open_job(self, value):
        self._open_job = value

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudStep) -> "UnrealOpenJobStep":
        """
        Create the instance of UnrealOpenJobStep from unreal.DeadlineCloudStep.
        Call same method on data_asset's environments.

        :param data_asset: unreal.DeadlineCloudStep instance

        :return: UnrealOpenJobStep instance
        :rtype: UnrealOpenJobStep
        """

        return cls(
            file_path=data_asset.path_to_template.file_path,
            name=data_asset.name,
            step_dependencies=list(data_asset.depends_on),
            environments=[
                UnrealOpenJobEnvironment.from_data_asset(env) for env in data_asset.environments
            ],
            host_requirements=HostRequirementsHelper.get_host_requirements_from_data_asset(
                data_asset.host_requirements
            ),
            extra_parameters=[
                UnrealOpenJobStepParameterDefinition.from_unreal_param_definition(param)
                for param in data_asset.get_step_parameters()
            ],
        )

    def _find_extra_parameter(
        self, parameter_name: str, parameter_type: str
    ) -> Optional[UnrealOpenJobStepParameterDefinition]:
        """
        Find extra parameter by given name and type

        :param parameter_name: Parameter name
        :param parameter_type: Parameter type (INT, FLOAT, STRING, PATH)

        :return: Parameter if found, None otherwise
        :rtype: Optional[UnrealOpenJobStepParameterDefinition]
        """
        return next(
            (
                p
                for p in self._extra_parameters
                if p.name == parameter_name and p.type == parameter_type
            ),
            None,
        )

    def _create_missing_extra_parameters_from_template(self):
        """
        Update parameters with YAML template data. Mostly needed for custom job submission process.

        If no template file found, skip updating and log warning.
        This is not an error and should not break the building process.
        """

        try:
            extra_param_names = [p.name for p in self._extra_parameters]
            for p in self.get_template_object()["parameterSpace"]["taskParameterDefinitions"]:
                if p["name"] not in extra_param_names:
                    self._extra_parameters.append(UnrealOpenJobStepParameterDefinition.from_dict(p))
        except FileNotFoundError:
            logger.warning("No template file found to read parameters from.")

    def _update_extra_parameter(
        self, extra_parameter: UnrealOpenJobStepParameterDefinition
    ) -> bool:
        """
        Update parameter by replacing existed parameter with given one
        after comparing them by name and type.

        :param extra_parameter: UnrealOpenJobStepParameterDefinition instance
        :type: UnrealOpenJobStepParameterDefinition

        :return: True if updated, False otherwise
        :rtype: bool
        """
        existed_parameter = self._find_extra_parameter(extra_parameter.name, extra_parameter.type)
        if existed_parameter:
            self._extra_parameters.remove(existed_parameter)
            self._extra_parameters.append(extra_parameter)
            return True
        return False

    def _check_parameters_consistency(self):
        """
        Check Step parameters consistency

        :return: Result of parameters consistency check
        :rtype: ParametersConsistencyCheckResult
        """

        result = ParametersConsistencyChecker.check_step_parameters_consistency(
            step_template_path=self.file_path,
            step_parameters=[p.to_dict() for p in self._extra_parameters],
        )

        result.reason = f'OpenJob Step "{self.name}": ' + result.reason

        return result

    def _build_step_parameter_definition_list(self) -> list:
        """
        Build the job parameter definition list from the step template object.

        Per https://github.com/OpenJobDescription/openjd-specifications/blob/mainline/rfcs/0001-task-chunking.md,
        If a task parameter is chunked, it must not be combined with any other task parameter using the associative operator.
        :raises ValueError: If CHUNK[INT] parameter is combined with associative operator

        :return: List of Step parameter definitions
        :rtype: list
        """

        step_template_object = self.get_template_object()

        step_parameter_definition_list = TaskParameterList()

        yaml_params = step_template_object["parameterSpace"]["taskParameterDefinitions"]
        combination = step_template_object["parameterSpace"].get("combination")

        # Check for CHUNK[INT] parameters and validate no associative operator
        has_chunk_int = any(p.get("type") == "CHUNK[INT]" for p in yaml_params)
        if has_chunk_int and combination == "*":
            raise ValueError("CHUNK[INT] parameter cannot be combined with associative operator")

        for yaml_p in yaml_params:
            override_param = next(
                (p for p in self._extra_parameters if p.name == yaml_p["name"]), None
            )
            if override_param:
                yaml_p["range"] = override_param.range
                # Also copy chunks config if present in override
                if override_param.chunks:
                    yaml_p["chunks"] = override_param.chunks

            param_type = yaml_p["type"]

            # CHUNK[INT] parameters are processed into STRING parameters with chunk values
            if param_type == "CHUNK[INT]":
                processed_param = self._process_chunk_int_parameter(yaml_p)
                # Parse into OpenJD StringTaskParameterDefinition
                param_descriptor = PARAMETER_DEFINITION_MAPPING["CHUNK[INT]"]
                param_definition_cls = param_descriptor.task_parameter_openjd_class
                step_parameter_definition_list.append(
                    parse_model(model=param_definition_cls, obj=processed_param)
                )
                continue

            param_descriptor: ParameterDefinitionDescriptor = PARAMETER_DEFINITION_MAPPING[
                param_type
            ]
            param_definition_cls = param_descriptor.task_parameter_openjd_class

            step_parameter_definition_list.append(
                parse_model(model=param_definition_cls, obj=yaml_p)
            )

        return step_parameter_definition_list

    def _process_chunk_int_parameter(self, yaml_param: dict) -> dict:
        """
        Process a CHUNK[INT] parameter and convert it to a STRING parameter
        with generated chunk values.

        :param yaml_param: The YAML parameter definition with type CHUNK[INT]

        :raises ValueError: If chunks configuration is invalid or missing

        :return: Modified parameter definition with type STRING and chunk values
        :rtype: dict
        """
        chunks_config = yaml_param.get("chunks")
        if not chunks_config:
            raise ValueError(
                f"CHUNK[INT] parameter '{yaml_param['name']}' must have 'chunks' configuration"
            )

        # Get configuration values
        default_task_count = chunks_config.get("defaultTaskCount")
        range_constraint_str = chunks_config.get("rangeConstraint", "NONCONTIGUOUS")
        target_runtime = chunks_config.get("targetRuntimeSeconds")

        # Validate defaultTaskCount
        if default_task_count is None:
            raise ValueError(
                f"CHUNK[INT] parameter '{yaml_param['name']}' must have 'defaultTaskCount' in chunks configuration"
            )

        # Convert to int if it's a string (could be a resolved parameter reference)
        try:
            default_task_count = int(default_task_count)
        except (ValueError, TypeError):
            raise ValueError(
                f"CHUNK[INT] parameter '{yaml_param['name']}': defaultTaskCount must be an integer, got '{default_task_count}'"
            )

        # Parse range constraint
        try:
            range_constraint = RangeConstraint(range_constraint_str)
        except ValueError:
            raise ValueError(
                f"CHUNK[INT] parameter '{yaml_param['name']}': rangeConstraint must be CONTIGUOUS or NONCONTIGUOUS, got '{range_constraint_str}'"
            )

        # Parse target runtime if provided
        target_runtime_int = None
        if target_runtime is not None:
            try:
                target_runtime_int = int(target_runtime)
            except (ValueError, TypeError):
                # If it's a parameter reference that wasn't resolved, ignore it
                pass

        # Create chunk configuration
        chunk_config = ChunkConfiguration(
            default_task_count=default_task_count,
            range_constraint=range_constraint,
            target_runtime_seconds=target_runtime_int,
        )

        # Get the range expression
        # If range is a list (from extra_parameters override), use the first element
        # or join them if they're pre-generated chunk values
        range_expr = yaml_param.get("range", "")
        if isinstance(range_expr, list):
            if len(range_expr) == 1:
                # Single element list - use as range expression
                range_expr = str(range_expr[0])
            elif len(range_expr) > 1:
                # Multiple elements - these are pre-generated chunk values, return as-is
                return {
                    "name": yaml_param["name"],
                    "type": "STRING",
                    "range": range_expr,
                }
            else:
                range_expr = ""

        if not range_expr:
            raise ValueError(
                f"CHUNK[INT] parameter '{yaml_param['name']}' must have a 'range' value"
            )

        # Create chunk parameter and generate values
        chunk_param = ChunkIntTaskParameter(
            name=yaml_param["name"],
            range_expr=range_expr,
            chunks=chunk_config,
        )

        chunk_values = chunk_param.generate_chunk_values()

        # Return modified parameter as STRING type with chunk values
        return {
            "name": yaml_param["name"],
            "type": "STRING",
            "range": chunk_values,
        }

    def _build_template(self) -> StepTemplate:
        """
        Build StepTemplate OpenJD model.

        Build process:
            1. Fill Step parameter definition list
            2. Fill Host Requirements if provided
            3. Build given Environments
            4. Set up Step dependencies

        :return: StepTemplate instance
        :rtype: StepTemplate
        """
        step_template_object = self.get_template_object()
        step_parameters = self._build_step_parameter_definition_list()

        template_dict = {
            "name": self.name,
            "script": parse_model(model=StepScript, obj=step_template_object["script"]),
        }

        if step_parameters:
            # Check if any CHUNK[INT] parameters are present (they're raw dicts)
            has_chunk_int = any(
                isinstance(p, dict) and p.get("type") == "CHUNK[INT]" for p in step_parameters
            )

            if has_chunk_int:
                # Build parameterSpace as raw dict for TASK_CHUNKING extension
                # Convert OpenJD models to dicts, keep CHUNK[INT] dicts as-is
                task_param_defs = []
                for p in step_parameters:
                    if isinstance(p, dict):
                        task_param_defs.append(p)
                    else:
                        # Convert OpenJD model to dict
                        task_param_defs.append(p.dict(exclude_none=True))

                template_dict["parameterSpace"] = {
                    "taskParameterDefinitions": task_param_defs,
                }
                combination = step_template_object["parameterSpace"].get("combination")
                if combination:
                    template_dict["parameterSpace"]["combination"] = combination
            else:
                template_dict["parameterSpace"] = StepParameterSpaceDefinition(
                    taskParameterDefinitions=step_parameters,
                    combination=step_template_object["parameterSpace"].get("combination"),
                )

        if self._environments:
            template_dict["stepEnvironments"] = [env.build_template() for env in self._environments]

        if self._step_dependencies:
            template_dict["dependencies"] = [
                StepDependency(dependsOn=step_dependency)
                for step_dependency in self._step_dependencies
            ]

        if self.host_requirements:
            template_dict["hostRequirements"] = self.host_requirements

        return parse_model(model=self.template_class, obj=template_dict)

    def get_asset_references(self):
        """
        Return AssetReferences of itself that union given Environments' AssetReferences

        :return: AssetReferences from this Step and its Environments
        :rtype: AssetReferences
        """
        asset_references = super().get_asset_references()
        for environment in self._environments:
            asset_references = asset_references.union(environment.get_asset_references())

        return asset_references

    def update_extra_parameter(self, extra_parameter: UnrealOpenJobStepParameterDefinition):
        """
        Public method for updating UnrealOpenJobStep's extra parameters.
        See _update_extra_parameter()

        :param extra_parameter: UnrealOpenJobStepParameterDefinition instance
        :type: UnrealOpenJobStepParameterDefinition

        :return: True if updated, False otherwise
        :rtype: bool
        """
        return self._update_extra_parameter(extra_parameter)


# Render Step
class RenderUnrealOpenJobStep(UnrealOpenJobStep):
    """
    Unreal Open Job Render Step entity
    """

    default_template_path = settings.RENDER_STEP_TEMPLATE_DEFAULT_PATH

    class RenderArgsType(IntEnum):
        """
        Type of the render arguments

        :cvar NOT_SET: Default value
        :cvar QUEUE_MANIFEST_PATH: Use manifest file with serialized MoviePipelineQueue
        :cvar RENDER_DATA: Use Level LevelSequence and MRQJobConfiguration unreal assets
        :cvar MRQ_ASSET: Use MoviePipelineQueue unreal asset
        """

        NOT_SET = 0
        QUEUE_MANIFEST_PATH = 1
        RENDER_DATA = 2
        MRQ_ASSET = 3

    def __init__(
        self,
        file_path: Optional[str] = None,
        name: Optional[str] = None,
        step_dependencies: Optional[list[str]] = None,
        environments: Optional[list] = None,
        extra_parameters: Optional[list] = None,
        host_requirements: Optional[HostRequirementsTemplate] = None,
        mrq_job: Optional[unreal.MoviePipelineExecutorJob] = None,
    ):
        """
        :param file_path: The file path of the step descriptor
        :type file_path: str

        :param name: The name of the step
        :type name: str

        :param step_dependencies: The list of step dependencies
        :type step_dependencies: list[str]

        :param environments: The list of environments
        :type environments: list

        :param extra_parameters: The list of extra parameters
        :type extra_parameters: list

        :param host_requirements: HostRequirements instance
        :type host_requirements: HostRequirements

        :param mrq_job: MRQ Job object
        :type mrq_job: unreal.MoviePipelineExecutorJob
        """

        super().__init__(
            file_path, name, step_dependencies, environments, extra_parameters, host_requirements
        )

        self._mrq_job = mrq_job
        self._queue_manifest_path: Optional[str] = None
        self._render_args_type = self._get_render_arguments_type()

    @property
    def mrq_job(self):
        return self._mrq_job

    @mrq_job.setter
    def mrq_job(self, value: unreal.MoviePipelineExecutorJob):
        self._mrq_job = value

    def _get_chunk_ids_count(self) -> int:
        """
        Get number of shot chunks
        as count of total number of frames divided by FramesPerTask if set, or
        as count of enabled shots in level sequence divided by chuck size parameter value.
        If no chunk size parameter value is 0, return 1

        Example:
            - LevelSequence shots: [sh1 - enabled, sh2 - disabled, sh3 - enabled, sh4 - enabled]
            - ChunkSize: 2
            - ChunkIds count: 2 (sh1, sh3; sh4)

        :raises ValueError: When no chunk size parameter is set

        :return: ChunkIds count
        :rtype: int
        """

        if not self.mrq_job:
            raise exceptions.MrqJobIsMissingError("MRQ Job must be provided")

        enabled_shots = [shot for shot in self.mrq_job.shot_info if shot.enabled]

        if not self.open_job:
            raise exceptions.OpenJobIsMissingError("Render Job must be provided")

        chunk_size_parameter = self.open_job._find_extra_parameter(
            parameter_name=OpenJobStepParameterNames.TASK_CHUNK_SIZE, parameter_type="INT"
        )
        frames_per_task_parameter = self.open_job._find_extra_parameter(
            parameter_name=OpenJobStepParameterNames.FRAMES_PER_TASK, parameter_type="INT"
        )
        if frames_per_task_parameter and frames_per_task_parameter.value > 0:
            logger.info(f"Rendering shots of frame range {frames_per_task_parameter.value}")
            level_sequence = self._load_level_sequence(self.mrq_job)
            output_settings = self._load_output_settings(self.mrq_job)

            if output_settings.use_custom_playback_range:
                total_frame_range = (
                    output_settings.custom_end_frame - output_settings.custom_start_frame
                )
                logger.info(
                    f"Output settings at submission has range {output_settings.custom_start_frame} - {output_settings.custom_end_frame} ({total_frame_range} frames)"
                )
            else:

                total_frame_range = (
                    level_sequence.get_playback_range().get_end_frame()
                    - level_sequence.get_playback_range().get_start_frame()
                )
                logger.info(
                    f"Level sequence at submission has range {level_sequence.get_playback_range()} ({total_frame_range} frames)"
                )
            task_chunk_ids_count = math.ceil(total_frame_range / frames_per_task_parameter.value)
            return task_chunk_ids_count
        if chunk_size_parameter is None:
            raise ValueError(
                f'Render Job\'s parameter "{OpenJobStepParameterNames.TASK_CHUNK_SIZE}"'
                f' or "{OpenJobStepParameterNames.FRAMES_PER_TASK}" '
                f"must be provided in extra parameters or template"
            )

        chunk_size = int(chunk_size_parameter.value)
        if chunk_size <= 0:
            chunk_size = 1  # by default 1 chunk consist of 1 shot

        task_chunk_ids_count = math.ceil(len(enabled_shots) / chunk_size)

        return task_chunk_ids_count

    def _load_level_sequence(self, mrq_job):
        """Load the level sequence asset from the MRQ job."""
        return unreal.EditorAssetLibrary.load_asset(
            unreal.SystemLibrary.conv_soft_object_reference_to_string(
                unreal.SystemLibrary.conv_soft_obj_path_to_soft_obj_ref(mrq_job.sequence)
            )
        )

    def _load_output_settings(self, mrq_job):
        """Load the output settings from the MRQ job configuration."""
        return mrq_job.get_configuration().find_setting_by_class(unreal.MoviePipelineOutputSetting)

    def _get_render_arguments_type(self) -> Optional["RenderUnrealOpenJobStep.RenderArgsType"]:
        """
        Return the render arguments type depending on Step parameters

        Priority of render argument type setting:
        - RenderArgsType.QUEUE_MANIFEST_PATH If QueueManifestPath parameter exists
        - RenderArgsType.MRQ_ASSET if MoviePipelineQueuePath parameter exists
        - RenderArgsType.RENDER_DATA If LevelPath, LevelSequencePath, MrqJobConfigurationPath
                                     parameters exists
        - RenderArgsType.NOT_SET if there are no valid parameters
        """
        parameter_names = [p.name for p in self._extra_parameters]
        for p in parameter_names:
            if p == OpenJobStepParameterNames.QUEUE_MANIFEST_PATH:
                return RenderUnrealOpenJobStep.RenderArgsType.QUEUE_MANIFEST_PATH
            if p == OpenJobStepParameterNames.MOVIE_PIPELINE_QUEUE_PATH:
                return RenderUnrealOpenJobStep.RenderArgsType.MRQ_ASSET
        if {
            OpenJobStepParameterNames.LEVEL_SEQUENCE_PATH,
            OpenJobStepParameterNames.LEVEL_PATH,
            OpenJobStepParameterNames.MRQ_JOB_CONFIGURATION_PATH,
        }.issubset(set(parameter_names)):
            return RenderUnrealOpenJobStep.RenderArgsType.RENDER_DATA

        return RenderUnrealOpenJobStep.RenderArgsType.NOT_SET

    def _build_template(self) -> StepTemplate:
        """
        Build StepTemplate OpenJD model.

        Build process:
            1. Forcibly update Step parameters listed in OpenJobStepParameterNames.
               If QueueManifestPath parameter exists, set up QueueManifestPath parameter definition
               and add it to Step Asset References.
            2. Fill Step parameter definition list
            3. Fill Host Requirements if provided
            4. Build given Environments
            5. Set up Step dependencies

        :return: StepTemplate instance
        :rtype: StepTemplate
        """

        if self._render_args_type == RenderUnrealOpenJobStep.RenderArgsType.NOT_SET:
            raise exceptions.RenderArgumentsTypeNotSetError(
                "RenderOpenJobStep parameters are not valid. Expect one of the following:\n"
                f"- {OpenJobStepParameterNames.QUEUE_MANIFEST_PATH}\n"
                f"- {OpenJobStepParameterNames.MOVIE_PIPELINE_QUEUE_PATH}\n"
                f"- ({OpenJobStepParameterNames.LEVEL_SEQUENCE_PATH}, "
                f"{OpenJobStepParameterNames.LEVEL_PATH}, "
                f"{OpenJobStepParameterNames.MRQ_JOB_CONFIGURATION_PATH})\n"
            )

        task_chunk_id_param_definition = UnrealOpenJobStepParameterDefinition(
            OpenJobStepParameterNames.TASK_CHUNK_ID,
            TaskParameterType.INT.value,
            [i for i in range(self._get_chunk_ids_count())],
        )
        self._update_extra_parameter(task_chunk_id_param_definition)

        handler_param_definition = UnrealOpenJobStepParameterDefinition(
            OpenJobStepParameterNames.ADAPTOR_HANDLER, TaskParameterType.STRING.value, ["render"]
        )
        self._update_extra_parameter(handler_param_definition)

        if self.mrq_job:
            output_setting = self.mrq_job.get_configuration().find_setting_by_class(
                unreal.MoviePipelineOutputSetting
            )
            output_path = output_setting.output_directory.path
            common.validate_path_does_not_contain_non_valid_chars(output_path)

            path_context = common.get_path_context_from_mrq_job(self.mrq_job)
            output_path = output_path.format_map(path_context).rstrip("/")
            output_param_definition = UnrealOpenJobStepParameterDefinition(
                OpenJobStepParameterNames.OUTPUT_PATH, TaskParameterType.PATH.value, [output_path]
            )
            self._update_extra_parameter(output_param_definition)

            if self._render_args_type == RenderUnrealOpenJobStep.RenderArgsType.QUEUE_MANIFEST_PATH:
                manifest_param_definition = UnrealOpenJobStepParameterDefinition(
                    OpenJobStepParameterNames.QUEUE_MANIFEST_PATH,
                    TaskParameterType.PATH.value,
                    [self._save_manifest_file()],
                )
                self._update_extra_parameter(manifest_param_definition)

        step_entity = super()._build_template()

        return step_entity

    def _save_manifest_file(self) -> Optional[str]:
        """
        Create new MoviePipelineQueue object, add given MRQ Job here and serialize it to .utxt file

        :return: Path to serialized manifest file
        :rtype: str
        """
        new_queue = unreal.MoviePipelineQueue()
        new_job = new_queue.duplicate_job(self.mrq_job)

        # In duplicated job remove empty auto-detected files since
        # we don't want them to be saved in manifest
        new_job.preset_overrides.job_attachments.input_files.auto_detected = (
            unreal.DeadlineCloudFileAttachmentsArray()
        )
        new_job.preset_overrides.job_attachments.input_directories.auto_detected_directories = (
            unreal.DeadlineCloudDirectoryAttachmentsArray()
        )

        _, manifest_path = unreal.MoviePipelineEditorLibrary.save_queue_to_manifest_file(new_queue)
        serialized_manifest = unreal.MoviePipelineEditorLibrary.convert_manifest_file_to_string(
            manifest_path
        )

        movie_render_pipeline_dir = os.path.join(
            unreal.SystemLibrary.get_project_saved_directory(),
            "UnrealDeadlineCloudService",
            "RenderJobManifests",
        )
        os.makedirs(movie_render_pipeline_dir, exist_ok=True)

        render_job_manifest_path = unreal.Paths.create_temp_filename(
            movie_render_pipeline_dir, prefix="RenderJobManifest", extension=".utxt"
        )

        with open(render_job_manifest_path, "w") as manifest:
            logger.info(f"Saving Manifest file `{render_job_manifest_path}`")
            manifest.write(serialized_manifest)

        self._queue_manifest_path = unreal.Paths.convert_relative_path_to_full(
            render_job_manifest_path
        )

        return self._queue_manifest_path

    def get_asset_references(self):
        """
        Return AssetReferences of itself that union given Environments' AssetReferences and
        add generated ManifestFile path if exists

        :return: AssetReferences from this Step and its Environments
        :rtype: AssetReferences
        """

        asset_references = super().get_asset_references()

        if self._queue_manifest_path:
            asset_references.input_filenames.add(self._queue_manifest_path)

        return asset_references


# Chunked Render Step (CHUNK[INT] support)
class ChunkedRenderUnrealOpenJobStep(RenderUnrealOpenJobStep):
    """
    Unreal Open Job Render Step entity using CHUNK[INT] task parameter type.

    This step uses the new OpenJD CHUNK[INT] parameter type to pass frame ranges
    directly to each task instead of using chunk IDs. This enables:
    - Direct frame range strings (e.g., "1-10") passed to workers
    - Support for both contiguous and non-contiguous ranges
    - Scheduler-side chunk size optimization via targetRuntimeSeconds

    The step calculates the frame range from the MRQ job and generates chunk
    values using the ChunkIntTaskParameter class.
    """

    default_template_path = settings.DYNAMIC_CHUNKING_RENDER_STEP_TEMPLATE_DEFAULT_PATH

    def __init__(
        self,
        file_path: Optional[str] = None,
        name: Optional[str] = None,
        step_dependencies: Optional[list[str]] = None,
        environments: Optional[list] = None,
        extra_parameters: Optional[list] = None,
        host_requirements: Optional[HostRequirementsTemplate] = None,
        mrq_job: Optional[unreal.MoviePipelineExecutorJob] = None,
        range_constraint: RangeConstraint = RangeConstraint.CONTIGUOUS,
    ):
        """
        :param file_path: The file path of the step descriptor
        :param name: The name of the step
        :param step_dependencies: The list of step dependencies
        :param environments: The list of environments
        :param extra_parameters: The list of extra parameters
        :param host_requirements: HostRequirements instance
        :param mrq_job: MRQ Job object
        :param range_constraint: Range constraint for chunk format (CONTIGUOUS or NONCONTIGUOUS)
        """
        super().__init__(
            file_path,
            name,
            step_dependencies,
            environments,
            extra_parameters,
            host_requirements,
            mrq_job,
        )
        self._range_constraint = range_constraint

    @property
    def range_constraint(self) -> RangeConstraint:
        return self._range_constraint

    @range_constraint.setter
    def range_constraint(self, value: RangeConstraint):
        self._range_constraint = value

    def _get_frame_range_from_mrq_job(self) -> tuple[int, int]:
        """
        Get the frame range from the MRQ job.

        :raises exceptions.MrqJobIsMissingError: If MRQ job is not provided

        :return: Tuple of (start_frame, end_frame) inclusive
        :rtype: tuple[int, int]
        """
        if not self.mrq_job:
            raise exceptions.MrqJobIsMissingError("MRQ Job must be provided")

        level_sequence = self._load_level_sequence(self.mrq_job)
        output_settings = self._load_output_settings(self.mrq_job)

        if output_settings.use_custom_playback_range:
            start_frame = output_settings.custom_start_frame
            end_frame = output_settings.custom_end_frame
        else:
            playback_range = level_sequence.get_playback_range()
            start_frame = playback_range.get_start_frame()
            end_frame = playback_range.get_end_frame()

        logger.info(f"Frame range from MRQ job: {start_frame}-{end_frame}")
        return (start_frame, end_frame)

    def _get_chunk_size(self) -> int:
        """
        Get the chunk size from the open job parameters.

        :raises exceptions.OpenJobIsMissingError: If open job is not provided
        :raises ValueError: If chunk size parameter is not found or invalid

        :return: Chunk size (frames per task)
        :rtype: int
        """
        if not self.open_job:
            raise exceptions.OpenJobIsMissingError("Render Job must be provided")

        # Try FramesPerTask first (takes precedence)
        frames_per_task_param = self.open_job._find_extra_parameter(
            parameter_name=OpenJobStepParameterNames.FRAMES_PER_TASK, parameter_type="INT"
        )
        if frames_per_task_param and frames_per_task_param.value > 0:
            return int(frames_per_task_param.value)

        # Fall back to ChunkSize
        chunk_size_param = self.open_job._find_extra_parameter(
            parameter_name=OpenJobStepParameterNames.TASK_CHUNK_SIZE, parameter_type="INT"
        )
        if chunk_size_param:
            chunk_size = int(chunk_size_param.value)
            if chunk_size > 0:
                return chunk_size

        raise ValueError(
            f'Render Job\'s parameter "{OpenJobStepParameterNames.TASK_CHUNK_SIZE}" '
            f'or "{OpenJobStepParameterNames.FRAMES_PER_TASK}" '
            f"must be provided with a positive value"
        )

    def _build_template(self) -> StepTemplate:
        """
        Build StepTemplate OpenJD model using CHUNK[INT] parameter.

        Build process:
            1. Calculate frame range from MRQ job
            2. Generate chunk values using ChunkIntTaskParameter
            3. Update Frame parameter with chunk values
            4. Set up Handler and other parameters
            5. Build the template using parent class logic

        :return: StepTemplate instance
        :rtype: StepTemplate
        """
        if self._render_args_type == RenderUnrealOpenJobStep.RenderArgsType.NOT_SET:
            raise exceptions.RenderArgumentsTypeNotSetError(
                "RenderOpenJobStep parameters are not valid. Expect one of the following:\n"
                f"- {OpenJobStepParameterNames.QUEUE_MANIFEST_PATH}\n"
                f"- {OpenJobStepParameterNames.MOVIE_PIPELINE_QUEUE_PATH}\n"
                f"- ({OpenJobStepParameterNames.LEVEL_SEQUENCE_PATH}, "
                f"{OpenJobStepParameterNames.LEVEL_PATH}, "
                f"{OpenJobStepParameterNames.MRQ_JOB_CONFIGURATION_PATH})\n"
            )

        # Get frame range and chunk size
        start_frame, end_frame = self._get_frame_range_from_mrq_job()
        chunk_size = self._get_chunk_size()

        # Create frame range expression
        from deadline.unreal_range_expr import RangeExpressionFormatter

        frame_range_expr = RangeExpressionFormatter.format_contiguous(start_frame, end_frame)

        # Create chunk configuration
        chunk_config = ChunkConfiguration(
            default_task_count=chunk_size,
            range_constraint=self._range_constraint,
        )

        # Generate chunk values
        chunk_param = ChunkIntTaskParameter(
            name=OpenJobStepParameterNames.FRAME_CHUNK,
            range_expr=frame_range_expr,
            chunks=chunk_config,
        )
        chunk_values = chunk_param.generate_chunk_values()

        logger.info(
            f"Generated {len(chunk_values)} chunks for frame range {frame_range_expr} "
            f"with chunk size {chunk_size}"
        )

        # Update Frame parameter with chunk values
        # Note: The template has CHUNK[INT] type, but we pre-generate the values
        # and pass them as the range. The _build_step_parameter_definition_list
        # will handle the CHUNK[INT] -> STRING conversion.
        frame_param_definition = UnrealOpenJobStepParameterDefinition(
            OpenJobStepParameterNames.FRAME_CHUNK,
            "CHUNK[INT]",
            chunk_values,  # Pre-generated chunk values
        )
        self._update_extra_parameter(frame_param_definition)

        # Set handler parameter
        handler_param_definition = UnrealOpenJobStepParameterDefinition(
            OpenJobStepParameterNames.ADAPTOR_HANDLER, TaskParameterType.STRING.value, ["render"]
        )
        self._update_extra_parameter(handler_param_definition)

        # Set output path if MRQ job is available
        if self.mrq_job:
            output_setting = self.mrq_job.get_configuration().find_setting_by_class(
                unreal.MoviePipelineOutputSetting
            )
            output_path = output_setting.output_directory.path
            common.validate_path_does_not_contain_non_valid_chars(output_path)

            path_context = common.get_path_context_from_mrq_job(self.mrq_job)
            output_path = output_path.format_map(path_context).rstrip("/")
            output_param_definition = UnrealOpenJobStepParameterDefinition(
                OpenJobStepParameterNames.OUTPUT_PATH, TaskParameterType.PATH.value, [output_path]
            )
            self._update_extra_parameter(output_param_definition)

            if self._render_args_type == RenderUnrealOpenJobStep.RenderArgsType.QUEUE_MANIFEST_PATH:
                manifest_param_definition = UnrealOpenJobStepParameterDefinition(
                    OpenJobStepParameterNames.QUEUE_MANIFEST_PATH,
                    TaskParameterType.PATH.value,
                    [self._save_manifest_file()],
                )
                self._update_extra_parameter(manifest_param_definition)

        # Build template using grandparent's method (skip RenderUnrealOpenJobStep._build_template)
        # since we've already set up the parameters
        return UnrealOpenJobStep._build_template(self)


# UGS Steps
class UgsRenderUnrealOpenJobStep(RenderUnrealOpenJobStep):
    """Class for predefined UGS Step"""

    default_template_path = settings.UGS_RENDER_STEP_TEMPLATE_DEFAULT_PATH


# Perforce (non UGS) Steps
class P4RenderUnrealOpenJobStep(RenderUnrealOpenJobStep):

    default_template_path = settings.P4_RENDER_STEP_TEMPLATE_DEFAULT_PATH
