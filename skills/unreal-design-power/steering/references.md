# References for Unreal Engine Design

## Unreal Engine APIs

### Python API
- **Documentation**: https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/
- **Key modules**: `unreal.MoviePipelineQueue`, `unreal.MoviePipelineExecutor`, `unreal.EditorAssetLibrary`

**Common Patterns:**
```python
# Load asset
asset = unreal.EditorAssetLibrary.load_asset("/Path/To/Asset")

# Movie Render Queue
subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
queue = movie_pipeline_queue_subsystem.get_queue()
render_job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
```

### C++ API
- **Documentation**: https://dev.epicgames.com/documentation/en-us/unreal-engine/API
- **Key classes**: `UMoviePipelineQueue`, `UMoviePipelineExecutorBase`, `UMovieSceneCaptureSettings`

### Additional Resources
- **Movie Render Pipeline**: https://dev.epicgames.com/documentation/en-us/unreal-engine/movie-render-pipeline-in-unreal-engine
- **Command Line Arguments**: https://dev.epicgames.com/documentation/en-us/unreal-engine/command-line-arguments-in-unreal-engine

## OpenJD Specifications

- **Repo**: https://github.com/OpenJobDescription/openjd-specifications

## AWS Deadline Cloud

- **API Reference**: https://docs.aws.amazon.com/deadline-cloud/latest/APIReference/
- **User Guide**: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/
- **Developer Guide**: https://docs.aws.amazon.com/deadline-cloud/latest/developerguide
- **Deadline Cloud Client**: https://github.com/aws-deadline/deadline-cloud

## Research Checklist

Before finalizing a design:
- [ ] Unreal Engine API usage is correct and up-to-date
- [ ] OpenJD template structure is valid
- [ ] Backwards compatibility assessed
- [ ] Performance implications considered
- [ ] Error cases handled
- [ ] Path mapping requirements addressed
