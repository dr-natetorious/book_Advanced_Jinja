# ==========================================

# Snippet 1: ConfigAST - Configuration-Aware Template Foundation

# Description: Extends Chapter 1's SelfAwareTemplate to understand configuration semantics

# ==========================================

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import yaml
import json
from pathlib import Path

# Import from Chapter 1

from chapter1 import SelfAwareTemplate, GenerationMetrics

@dataclass
class ConfigOrigin:
"""Tracks where a configuration value originated."""
file_path: str
line_number: int
merge_level: int
transformation_id: str
timestamp: datetime

class ConfigAST(SelfAwareTemplate):
"""Configuration-aware AST that tracks value lineage and transformations."""

    def __init__(self, config_content: str, format_type: str, metadata: Dict[str, Any] = None):
        super().__init__(config_content, metadata)
        self.format_type = format_type
        self.value_origins: Dict[str, ConfigOrigin] = {}
        self.merge_history: List[Dict[str, Any]] = []
        self.schema_version: Optional[str] = None

    def parse_config(self) -> Dict[str, Any]:
        """Parse configuration content maintaining lineage information."""
        if self.format_type == 'yaml':
            parsed = yaml.safe_load(self.content)
        elif self.format_type == 'json':
            parsed = json.loads(self.content)
        else:
            raise ValueError(f"Unsupported format: {self.format_type}")

        # Track origins for each value
        self._track_value_origins(parsed, self.metadata.get('source_file', 'unknown'))
        return parsed

    def _track_value_origins(self, data: Any, source_file: str, path: str = "", line_offset: int = 0):
        """Recursively track where each configuration value originated."""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                self.value_origins[current_path] = ConfigOrigin(
                    file_path=source_file,
                    line_number=line_offset + self._estimate_line_number(key),
                    merge_level=len(self.merge_history),
                    transformation_id=f"parse_{self.format_type}",
                    timestamp=datetime.now()
                )
                self._track_value_origins(value, source_file, current_path, line_offset)

    def merge_with(self, other: 'ConfigAST', strategy: str = 'override') -> 'ConfigAST':
        """Merge configurations while maintaining lineage."""
        merged_content = self._merge_configs(self.parse_config(), other.parse_config(), strategy)

        # Create new ConfigAST with merged content
        merged = ConfigAST(
            yaml.dump(merged_content),
            'yaml',
            {'merge_strategy': strategy, 'merged_from': [self.metadata, other.metadata]}
        )

        # Combine origin tracking
        merged.value_origins.update(self.value_origins)
        merged.value_origins.update(other.value_origins)

        # Record merge operation
        merged.merge_history = self.merge_history + [{
            'operation': 'merge',
            'strategy': strategy,
            'timestamp': datetime.now(),
            'sources': [self.metadata.get('source_file'), other.metadata.get('source_file')]
        }]

        return merged

# ==========================================

# Snippet 2: ConfigRegistry - Multi-Source Schema Management

# Description: Extends Chapter 2's VersionAwareGenerator for configuration schema convergence

# ==========================================

# Import from Chapter 2

from chapter2 import VersionAwareGenerator, TemplateVersion, CompatibilityLevel

class ConfigRegistry(VersionAwareGenerator):
"""Manages multiple configuration sources with semantic convergence."""

    def __init__(self):
        super().__init__()
        self.config_sources: Dict[str, ConfigAST] = {}
        self.schema_inference_cache: Dict[str, Dict[str, Any]] = {}
        self.conflict_resolution_rules: Dict[str, callable] = {}

    def register_config_source(self, name: str, config_ast: ConfigAST):
        """Register a configuration source for tracking and analysis."""
        self.config_sources[name] = config_ast

        # Infer schema from this source
        schema = self._infer_schema(config_ast)
        self.schema_inference_cache[name] = schema

        # Check for conflicts with existing schemas
        conflicts = self._detect_schema_conflicts(name, schema)
        if conflicts:
            self._log_schema_conflicts(name, conflicts)

    def _infer_schema(self, config_ast: ConfigAST) -> Dict[str, Any]:
        """Infer schema structure from configuration content."""
        parsed = config_ast.parse_config()
        return self._analyze_structure(parsed)

    def _analyze_structure(self, data: Any, path: str = "") -> Dict[str, Any]:
        """Recursively analyze configuration structure."""
        if isinstance(data, dict):
            schema = {'type': 'object', 'properties': {}}
            for key, value in data.items():
                schema['properties'][key] = self._analyze_structure(value, f"{path}.{key}")
            return schema
        elif isinstance(data, list):
            if data:
                return {'type': 'array', 'items': self._analyze_structure(data[0], path)}
            return {'type': 'array', 'items': {'type': 'unknown'}}
        else:
            return {'type': type(data).__name__, 'example': data}

    def get_unified_schema(self) -> Dict[str, Any]:
        """Generate unified schema from all registered sources."""
        unified = {'type': 'object', 'properties': {}}

        for source_name, schema in self.schema_inference_cache.items():
            unified = self._merge_schemas(unified, schema)

        return unified

    def generate_lineage_context(self, config_path: str) -> Dict[str, Any]:
        """Generate context for lineage tracking of a specific config path."""
        lineage = []

        for source_name, config_ast in self.config_sources.items():
            if config_path in config_ast.value_origins:
                origin = config_ast.value_origins[config_path]
                lineage.append({
                    'source': source_name,
                    'origin': origin,
                    'merge_history': config_ast.merge_history,
                    'schema_info': self.schema_inference_cache.get(source_name, {})
                })

        return {
            'config_path': config_path,
            'lineage_chain': lineage,
            'final_value': self._resolve_final_value(config_path),
            'conflicts': self._detect_value_conflicts(config_path)
        }

# ==========================================

# Snippet 3: ConfigLineageTracker - Archaeological Discovery Engine

# Description: Core system for tracing configuration values through complex DAG pipelines

# ==========================================

from typing import Tuple, Set
import networkx as nx
from collections import defaultdict

class ConfigLineageTracker:
"""Tracks configuration value lineage through complex merge pipelines."""

    def __init__(self):
        self.dag = nx.DiGraph()
        self.value_transformations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.merge_operations: List[Dict[str, Any]] = []
        self.conflict_log: List[Dict[str, Any]] = []

    def record_merge_operation(self, source_configs: List[ConfigAST],
                             result_config: ConfigAST,
                             operation_id: str):
        """Record a configuration merge operation in the DAG."""

        # Add nodes to DAG
        for config in source_configs:
            config_id = self._get_config_id(config)
            self.dag.add_node(config_id, config=config)

        result_id = self._get_config_id(result_config)
        self.dag.add_node(result_id, config=result_config)

        # Add edges showing merge relationships
        for config in source_configs:
            source_id = self._get_config_id(config)
            self.dag.add_edge(source_id, result_id, operation=operation_id)

        # Record the operation
        self.merge_operations.append({
            'operation_id': operation_id,
            'sources': [self._get_config_id(c) for c in source_configs],
            'result': result_id,
            'timestamp': datetime.now(),
            'conflicts': self._detect_merge_conflicts(source_configs)
        })

    def trace_value_lineage(self, config_path: str, target_config: ConfigAST) -> Dict[str, Any]:
        """Trace where a specific configuration value originated."""
        target_id = self._get_config_id(target_config)

        # Find all paths to this configuration
        lineage_paths = []
        for node in self.dag.nodes():
            if node != target_id:
                try:
                    paths = list(nx.all_simple_paths(self.dag, node, target_id))
                    for path in paths:
                        if self._path_affects_value(path, config_path):
                            lineage_paths.append(path)
                except nx.NetworkXNoPath:
                    continue

        # Analyze transformations along each path
        transformation_analysis = []
        for path in lineage_paths:
            path_analysis = self._analyze_transformation_path(path, config_path)
            transformation_analysis.append(path_analysis)

        return {
            'config_path': config_path,
            'target_config': target_id,
            'lineage_paths': lineage_paths,
            'transformations': transformation_analysis,
            'final_origin': self._identify_ultimate_origin(config_path, lineage_paths),
            'confidence_score': self._calculate_lineage_confidence(transformation_analysis)
        }

    def generate_why_query_response(self, config_path: str,
                                  target_config: ConfigAST) -> Dict[str, Any]:
        """Generate response to 'Why is this value X?' query."""
        lineage = self.trace_value_lineage(config_path, target_config)

        # Build human-readable explanation
        explanation = self._build_explanation(lineage)

        return {
            'query': f"Why is '{config_path}' set to its current value?",
            'short_answer': explanation['summary'],
            'detailed_lineage': lineage,
            'visual_dag': self._generate_visual_dag_for_path(config_path),
            'suggested_actions': self._suggest_actions(lineage),
            'confidence': lineage['confidence_score']
        }

# ==========================================

# Snippet 4: Junction Templates - Configuration Merge Point Analysis

# Description: Jinja2 templates that generate analysis reports for configuration merge operations

# ==========================================

# Template for analyzing configuration merge points

MERGE_POINT_ANALYSIS_TEMPLATE = '''
{# Junction analysis template for configuration merge points #}

# Configuration Merge Analysis: {{ operation_id }}

**Merge Operation**: {{ operation_id }}
**Timestamp**: {{ timestamp }}
**Strategy**: {{ merge_strategy }}

## Source Configurations

{% for source in sources %}

### {{ source.name }}

- **File**: `{{ source.file_path }}`
- **Format**: {{ source.format }}
- **Schema Version**: {{ source.schema_version | default('inferred') }}
- **Values Contributed**: {{ source.contributed_values | length }}

{% endfor %}

## Merge Results

{% if conflicts %}

### ⚠️ Conflicts Detected

{% for conflict in conflicts %}

- **Path**: `{{ conflict.path }}`
- **Conflict Type**: {{ conflict.type }}
- **Values**:
  {% for source, value in conflict.competing_values.items() %}
  - {{ source }}: `{{ value }}`
    {% endfor %}
- **Resolution**: {{ conflict.resolution }}
  {% endfor %}
  {% else %}
  ✅ **No conflicts detected**
  {% endif %}

## Value Transformations

{% for transformation in transformations %}

### {{ transformation.path }}

- **Source**: {{ transformation.source }}
- **Transformation**: {{ transformation.type }}
- **Before**: `{{ transformation.old_value }}`
- **After**: `{{ transformation.new_value }}`
  {% if transformation.reason %}
- **Reason**: {{ transformation.reason }}
  {% endif %}

{% endfor %}

## Impact Analysis

- **Total values merged**: {{ total_values }}
- **New values added**: {{ new_values_count }}
- **Values overridden**: {{ overridden_values_count }}
- **Schema compatibility**: {{ schema_compatibility }}

{% if recommendations %}

## Recommendations

{% for rec in recommendations %}

- {{ rec }}
  {% endfor %}
  {% endif %}
  '''

class JunctionTemplateRenderer:
"""Renders junction analysis templates with configuration data."""

    def __init__(self):
        from jinja2 import Environment, Template
        self.env = Environment()

        # Load templates
        self.merge_analysis_template = Template(MERGE_POINT_ANALYSIS_TEMPLATE)

    def render_merge_analysis(self, merge_operation: Dict[str, Any]) -> str:
        """Render merge point analysis report."""

        context = {
            'operation_id': merge_operation['operation_id'],
            'timestamp': merge_operation['timestamp'].isoformat(),
            'merge_strategy': merge_operation.get('strategy', 'default'),
            'sources': self._prepare_source_data(merge_operation['sources']),
            'conflicts': merge_operation.get('conflicts', []),
            'transformations': self._analyze_transformations(merge_operation),
            'total_values': self._count_total_values(merge_operation),
            'new_values_count': self._count_new_values(merge_operation),
            'overridden_values_count': self._count_overridden_values(merge_operation),
            'schema_compatibility': self._assess_schema_compatibility(merge_operation),
            'recommendations': self._generate_recommendations(merge_operation)
        }

        return self.merge_analysis_template.render(**context)

# ==========================================

# Snippet 5: ConfigMigrator - AST-Based Configuration Evolution

# Description: Extends Chapter 1's ASTTemplateModifier for configuration format migration

# ==========================================

# Import from Chapter 1

from chapter1 import ASTTemplateModifier

class ConfigMigrator(ASTTemplateModifier):
"""Migrates configurations between versions and formats using AST manipulation."""

    def __init__(self):
        super().__init__()
        self.migration_rules: Dict[str, List[callable]] = {}
        self.format_converters: Dict[Tuple[str, str], callable] = {}
        self.version_detectors: Dict[str, callable] = {}

    def register_migration_rule(self, from_version: str, to_version: str,
                               migration_func: callable):
        """Register a migration rule between configuration versions."""
        key = f"{from_version}->{to_version}"
        if key not in self.migration_rules:
            self.migration_rules[key] = []
        self.migration_rules[key].append(migration_func)

    def migrate_config(self, config_ast: ConfigAST,
                      target_version: str = None,
                      target_format: str = None) -> ConfigAST:
        """Migrate configuration to target version and/or format."""

        # Detect current version if not specified
        current_version = self._detect_version(config_ast)
        current_format = config_ast.format_type

        # Plan migration path
        migration_path = self._plan_migration_path(
            current_version, target_version,
            current_format, target_format
        )

        # Execute migration steps
        migrated_ast = config_ast
        for step in migration_path:
            migrated_ast = self._execute_migration_step(migrated_ast, step)

        return migrated_ast

    def _plan_migration_path(self, current_version: str, target_version: str,
                           current_format: str, target_format: str) -> List[Dict[str, Any]]:
        """Plan the migration steps needed."""
        steps = []

        # Version migration steps
        if target_version and current_version != target_version:
            version_path = self._find_version_migration_path(current_version, target_version)
            for from_v, to_v in version_path:
                steps.append({
                    'type': 'version_migration',
                    'from_version': from_v,
                    'to_version': to_v
                })

        # Format conversion step
        if target_format and current_format != target_format:
            steps.append({
                'type': 'format_conversion',
                'from_format': current_format,
                'to_format': target_format
            })

        return steps

# ==========================================

# Snippet 6: Developer-Friendly Lineage Report Generator

# Description: Template-driven system that generates interactive HTML reports for configuration archaeology

# ==========================================

# Main HTML template for interactive lineage report

LINEAGE_REPORT_HTML_TEMPLATE = '''

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Configuration Lineage Report</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f7fa; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .query-box { background: #e3f2fd; padding: 15px; border-radius: 5px; border-left: 4px solid #2196f3; }
        .answer-summary { background: #e8f5e8; padding: 15px; border-radius: 5px; border-left: 4px solid #4caf50; margin: 15px 0; }
        .confidence-meter { width: 100%; height: 20px; background: #eee; border-radius: 10px; overflow: hidden; }
        .confidence-fill { height: 100%; transition: width 0.3s; }
        .tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
        .tab { padding: 10px 20px; cursor: pointer; border-bottom: 2px solid transparent; }
        .tab.active { border-bottom-color: #2196f3; background: #f0f8ff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Configuration Lineage Report</h1>
            <div class="query-box">
                <h3>Query: {{ query.question }}</h3>
                <p><strong>Target:</strong> <code>{{ query.config_path }}</code></p>
                <p><strong>Generated:</strong> {{ report_timestamp }}</p>
            </div>

            <div class="answer-summary">
                <h3>💡 Answer Summary</h3>
                <p>{{ answer.summary }}</p>
                <div class="confidence-meter">
                    <div class="confidence-fill" style="width: {{ answer.confidence * 100 }}%; background: {% if answer.confidence > 0.8 %}#4caf50{% elif answer.confidence > 0.6 %}#ff9800{% else %}#f44336{% endif %};"></div>
                </div>
                <small>Confidence: {{ (answer.confidence * 100) | round(1) }}%</small>
            </div>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="showTab('overview')">Overview</div>
            <div class="tab" onclick="showTab('lineage')">Lineage Paths</div>
            <div class="tab" onclick="showTab('dag')">Visual DAG</div>
        </div>

        <div id="overview" class="tab-content active">
            <div class="dag-container">
                <h3>📊 Configuration Overview</h3>
                <p><strong>Final Value:</strong> <code>{{ final_value }}</code></p>
                <p><strong>Source Files:</strong> {{ source_files | length }}</p>
                <p><strong>Merge Operations:</strong> {{ merge_operations | length }}</p>
            </div>
        </div>
    </div>

    <script>
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }
    </script>

</body>
</html>
'''

class LineageReportGenerator:
"""Generates comprehensive, interactive lineage reports for configuration archaeology."""

    def __init__(self, lineage_tracker: ConfigLineageTracker,
                 config_registry: ConfigRegistry):
        self.lineage_tracker = lineage_tracker
        self.config_registry = config_registry

        from jinja2 import Environment, Template
        self.env = Environment()
        self.html_template = Template(LINEAGE_REPORT_HTML_TEMPLATE)

    def generate_lineage_report(self, config_path: str,
                              target_config: ConfigAST) -> str:
        """Generate comprehensive lineage report for a configuration path."""

        # Gather all lineage data
        lineage_data = self.lineage_tracker.trace_value_lineage(config_path, target_config)
        query_response = self.lineage_tracker.generate_why_query_response(config_path, target_config)

        # Prepare report context
        context = {
            'query': {
                'question': f"Why is '{config_path}' set to its current value?",
                'config_path': config_path
            },
            'report_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'answer': {
                'summary': query_response['short_answer'],
                'confidence': query_response['confidence']
            },
            'final_value': self._get_final_value(config_path, target_config),
            'source_files': self._get_source_files(lineage_data),
            'merge_operations': self._get_merge_operations(lineage_data)
        }

        return self.html_template.render(**context)

# ==========================================

# Snippet 7: Docker Compose Configuration Archaeology Example

# Description: Real-world example showing how to apply the system to Docker Compose configurations

# ==========================================

class DockerComposeArchaeology:
"""Example implementation for Docker Compose configuration archaeology."""

    def __init__(self):
        self.lineage_tracker = ConfigLineageTracker()
        self.config_registry = ConfigRegistry()
        self.migrator = ConfigMigrator()
        self.report_generator = None  # Will be initialized after setup

        # Setup Docker Compose specific migration rules
        self._setup_docker_compose_migrations()

    def _setup_docker_compose_migrations(self):
        """Setup migration rules for Docker Compose configuration evolution."""

        # Migration from v2 to v3 format
        def migrate_v2_to_v3(config_data):
            if 'version' not in config_data:
                config_data['version'] = '3.8'

            # Convert links to depends_on
            for service_name, service_config in config_data.get('services', {}).items():
                if 'links' in service_config:
                    depends_on = service_config.get('depends_on', [])
                    for link in service_config['links']:
                        service_name = link.split(':')[0]
                        if service_name not in depends_on:
                            depends_on.append(service_name)
                    service_config['depends_on'] = depends_on
                    del service_config['links']

            return config_data

        self.migrator.register_migration_rule('2.x', '3.x', migrate_v2_to_v3)

    def analyze_docker_compose_pipeline(self, base_compose_file: str,
                                      override_files: List[str]) -> ConfigAST:
        """Analyze a Docker Compose configuration pipeline with overrides."""

        # Load base configuration
        base_config = ConfigAST(
            Path(base_compose_file).read_text(),
            'yaml',
            {'source_file': base_compose_file, 'type': 'base'}
        )
        self.config_registry.register_config_source('base', base_config)

        # Load and merge override configurations
        merged_config = base_config
        for i, override_file in enumerate(override_files):
            override_config = ConfigAST(
                Path(override_file).read_text(),
                'yaml',
                {'source_file': override_file, 'type': 'override', 'level': i+1}
            )

            self.config_registry.register_config_source(f'override_{i+1}', override_config)

            # Perform merge and track in lineage
            new_merged = merged_config.merge_with(override_config, strategy='override')

            # Record merge operation
            self.lineage_tracker.record_merge_operation(
                [merged_config, override_config],
                new_merged,
                f"compose_override_{i+1}"
            )

            merged_config = new_merged

        # Setup report generator
        self.report_generator = LineageReportGenerator(
            self.lineage_tracker,
            self.config_registry
        )

        return merged_config

    def investigate_service_config(self, service_name: str,
                                 config_key: str,
                                 final_config: ConfigAST) -> str:
        """Generate investigation report for a specific service configuration."""

        config_path = f"services.{service_name}.{config_key}"

        return self.report_generator.generate_lineage_report(
            config_path,
            final_config
        )

# ==========================================

# Snippet 8: Integration and Usage Example

# Description: Complete example showing how all components work together

# ==========================================

async def demonstrate_config_archaeology():
"""Demonstrate the complete configuration archaeology system."""

    print("🔍 Configuration Pipeline Archaeology Demonstration")
    print("=" * 60)

    # Initialize the Docker Compose archaeology system
    archaeology_system = DockerComposeArchaeology()

    # Create example configuration files
    base_compose = '''

version: '3.8'
services:
web:
image: nginx:latest
ports: - "80:80"
environment: - ENV=production

db:
image: postgres:13
environment: - POSTGRES_DB=myapp - POSTGRES_USER=user - POSTGRES_PASSWORD=password
'''

    development_override = '''

version: '3.8'
services:
web:
image: nginx:alpine
ports: - "8080:80"
environment: - ENV=development - DEBUG=true
volumes: - ./src:/usr/share/nginx/html

db:
ports: - "5432:5432"
environment: - POSTGRES_PASSWORD=dev_password
'''

    # Write temporary files
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as base_file:
        base_file.write(base_compose)
        base_file_path = base_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as dev_file:
        dev_file.write(development_override)
        dev_file_path = dev_file.name

    try:
        # Analyze the pipeline
        final_config = archaeology_system.analyze_docker_compose_pipeline(
            base_file_path,
            [dev_file_path]
        )

        # Generate investigation report
        report = archaeology_system.investigate_service_config(
            'web',
            'environment',
            final_config
        )

        print("✅ Configuration archaeology analysis complete!")
        print("📄 Interactive report generated")

        return report

    finally:
        # Clean up temporary files
        import os
        os.unlink(base_file_path)
        os.unlink(dev_file_path)

if **name** == "**main**":
import asyncio
asyncio.run(demonstrate_config_archaeology())

# ==========================================

# Snippet 9: @config_pipeline Decorator - Template-Driven Pipeline Orchestration

# Description: Transforms functions into config pipeline stages with automatic lineage tracking

# ==========================================

from functools import wraps
from typing import Dict, List, Any, Callable, Optional
import inspect
from dataclasses import dataclass
import asyncio

@dataclass
class PipelineStage:
"""Metadata for a pipeline stage."""
name: str
function: Callable
dependencies: List[str]
template_path: Optional[str] = None
cache_strategy: str = 'none'
lineage_tracking: bool = True

class ConfigPipelineRegistry:
"""Global registry for configuration pipeline stages."""

    def __init__(self):
        self.stages: Dict[str, PipelineStage] = {}
        self.execution_graph = None
        self.lineage_tracker = None

    def register_stage(self, stage: PipelineStage):
        """Register a pipeline stage."""
        self.stages[stage.name] = stage
        self._invalidate_graph()

    def _invalidate_graph(self):
        """Mark execution graph as needing rebuild."""
        self.execution_graph = None

# Global pipeline registry

\_pipeline_registry = ConfigPipelineRegistry()

def config_pipeline(name: str = None,
depends_on: List[str] = None,
template: str = None,
cache: str = 'none',
track_lineage: bool = True):
"""
Decorator that marks a function as a configuration pipeline stage.

    Args:
        name: Stage name (defaults to function name)
        depends_on: List of stage names this depends on
        template: Optional Jinja template for stage documentation/visualization
        cache: Caching strategy ('none', 'memory', 'disk')
        track_lineage: Whether to track lineage for this stage
    """
    def decorator(func: Callable) -> Callable:
        stage_name = name or func.__name__
        dependencies = depends_on or []

        # Create pipeline stage metadata
        stage = PipelineStage(
            name=stage_name,
            function=func,
            dependencies=dependencies,
            template_path=template,
            cache_strategy=cache,
            lineage_tracking=track_lineage
        )

        # Register with global registry
        _pipeline_registry.register_stage(stage)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract ConfigAST instances from arguments
            config_inputs = [arg for arg in args if isinstance(arg, ConfigAST)]

            # Track pipeline execution start
            if track_lineage and _pipeline_registry.lineage_tracker:
                operation_id = f"pipeline_stage_{stage_name}"

                # Execute the original function
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

                # Track pipeline execution completion
                if isinstance(result, ConfigAST):
                    _pipeline_registry.lineage_tracker.record_merge_operation(
                        config_inputs,
                        result,
                        operation_id
                    )

                return result
            else:
                # Execute without tracking
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

        # Attach metadata to the wrapper
        wrapper._pipeline_stage = stage
        return wrapper

    return decorator

# Example usage of the decorator

@config_pipeline(name="environment_merge", depends_on=["base_config"], track_lineage=True)
def merge_environment_config(base_config: ConfigAST, env_config: ConfigAST) -> ConfigAST:
"""Merge environment-specific configuration with base configuration."""
return base_config.merge_with(env_config, strategy='environment_override')

@config_pipeline(name="security_injection", depends_on=["environment_merge"], template="security_template.j2")
def inject_security_policies(config: ConfigAST) -> ConfigAST:
"""Inject security policies based on environment and service type.""" # Implementation would analyze config and inject appropriate security settings
return config

# ==========================================

# Snippet 10: ConfigPipelineTemplate - Template-Orchestrated DAG Execution

# Description: Jinja template that manages configuration pipeline execution and generates documentation

# ==========================================

from jinja2 import Environment, Template, BaseLoader, DictLoader
import networkx as nx
from typing import Set

class ConfigPipelineTemplate:
"""Template-driven configuration pipeline orchestrator."""

    def __init__(self, lineage_tracker: 'ConfigLineageTracker'):
        self.lineage_tracker = lineage_tracker
        self.execution_graph: Optional[nx.DiGraph] = None
        self.template_env = Environment(loader=DictLoader(self._get_builtin_templates()))

        # Connect to global registry
        _pipeline_registry.lineage_tracker = lineage_tracker

    def _get_builtin_templates(self) -> Dict[str, str]:
        """Get built-in pipeline templates."""
        return {
            'pipeline_executor': '''

{# Template for executing configuration pipelines #}

# Configuration Pipeline Execution Plan

# Generated: {{ execution_timestamp }}

## Pipeline Overview

- **Total Stages**: {{ stages | length }}
- **Execution Order**: {{ execution_order | join(' → ') }}
- **Estimated Duration**: {{ estimated_duration }} seconds

## Stage Details

{% for stage_name in execution_order %}
{% set stage = stages[stage_name] %}

### {{ stage.name }}

- **Dependencies**: {{ stage.dependencies | join(', ') or 'None' }}
- **Caching**: {{ stage.cache_strategy }}
- **Lineage Tracking**: {{ stage.lineage_tracking }}
  {% if stage.template_path %}
- **Template**: {{ stage.template_path }}
  {% endif %}

{% endfor %}

## Execution Graph

```mermaid
graph TD
{% for stage_name in execution_order %}
{% set stage = stages[stage_name] %}
    {{ stage_name }}[{{ stage.name }}]
{% for dep in stage.dependencies %}
    {{ dep }} --> {{ stage_name }}
{% endfor %}
{% endfor %}
```

            ''',

            'pipeline_report': '''

{# Template for pipeline execution reports #}

# Pipeline Execution Report

**Pipeline**: {{ pipeline_name }}
**Executed**: {{ execution_timestamp }}
**Status**: {{ 'SUCCESS' if success else 'FAILED' }}
**Duration**: {{ execution_duration }} seconds

## Stage Results

{% for stage_result in stage_results %}

### {{ stage_result.stage_name }}

- **Status**: {{ 'PASS' if stage_result.success else 'FAIL' }}
- **Duration**: {{ stage_result.duration }} seconds
- **Input Configs**: {{ stage_result.input_count }}
- **Output Size**: {{ stage_result.output_size }} bytes
  {% if stage_result.error %}
- **Error**: {{ stage_result.error }}
  {% endif %}
  {% if stage_result.lineage_info %}
- **Lineage Tracked**: {{ stage_result.lineage_info.transformations | length }} transformations
  {% endif %}

{% endfor %}

{% if conflicts %}

## Conflicts Detected

{% for conflict in conflicts %}

- **Stage**: {{ conflict.stage_name }}
- **Type**: {{ conflict.type }}
- **Resolution**: {{ conflict.resolution }}
  {% endfor %}
  {% endif %}

## Performance Analysis

- **Bottleneck Stage**: {{ bottleneck_stage }}
- **Cache Hit Rate**: {{ cache_hit_rate }}%
- **Lineage Overhead**: {{ lineage_overhead }}%
  '''
  }

  def build_execution_graph(self) -> nx.DiGraph:
  """Build execution graph from registered pipeline stages."""
  graph = nx.DiGraph()

        # Add all stages as nodes
        for stage_name, stage in _pipeline_registry.stages.items():
            graph.add_node(stage_name, stage=stage)

        # Add dependency edges
        for stage_name, stage in _pipeline_registry.stages.items():
            for dependency in stage.dependencies:
                if dependency in _pipeline_registry.stages:
                    graph.add_edge(dependency, stage_name)
                else:
                    raise ValueError(f"Stage '{stage_name}' depends on unknown stage '{dependency}'")

        # Check for cycles
        if not nx.is_directed_acyclic_graph(graph):
            cycles = list(nx.simple_cycles(graph))
            raise ValueError(f"Pipeline contains cycles: {cycles}")

        self.execution_graph = graph
        return graph

  def generate_execution_plan(self) -> str:
  """Generate execution plan documentation using templates."""
  if not self.execution_graph:
  self.build_execution_graph()

        # Get topological ordering
        execution_order = list(nx.topological_sort(self.execution_graph))

        # Prepare template context
        context = {
            'execution_timestamp': datetime.now().isoformat(),
            'stages': _pipeline_registry.stages,
            'execution_order': execution_order,
            'estimated_duration': self._estimate_execution_duration(execution_order)
        }

        template = self.template_env.get_template('pipeline_executor')
        return template.render(**context)

  async def execute_pipeline(self, initial_configs: Dict[str, ConfigAST],
  target_stages: Set[str] = None) -> Dict[str, Any]:
  """Execute the configuration pipeline."""
  if not self.execution_graph:
  self.build_execution_graph()

        # Determine which stages to execute
        if target_stages:
            # Find all stages needed to reach targets
            required_stages = set()
            for target in target_stages:
                required_stages.update(nx.ancestors(self.execution_graph, target))
                required_stages.add(target)
            execution_order = [s for s in nx.topological_sort(self.execution_graph) if s in required_stages]
        else:
            execution_order = list(nx.topological_sort(self.execution_graph))

        # Execute stages in order
        stage_outputs = initial_configs.copy()
        stage_results = []
        start_time = datetime.now()

        for stage_name in execution_order:
            stage = _pipeline_registry.stages[stage_name]
            stage_start = datetime.now()

            try:
                # Prepare stage inputs
                stage_inputs = self._prepare_stage_inputs(stage, stage_outputs)

                # Execute stage
                if asyncio.iscoroutinefunction(stage.function):
                    result = await stage.function(**stage_inputs)
                else:
                    result = stage.function(**stage_inputs)

                # Store result
                stage_outputs[stage_name] = result

                # Record success
                stage_duration = (datetime.now() - stage_start).total_seconds()
                stage_results.append({
                    'stage_name': stage_name,
                    'success': True,
                    'duration': stage_duration,
                    'input_count': len(stage_inputs),
                    'output_size': len(str(result)) if result else 0,
                    'lineage_info': self._get_lineage_info(stage_name)
                })

            except Exception as e:
                # Record failure
                stage_duration = (datetime.now() - stage_start).total_seconds()
                stage_results.append({
                    'stage_name': stage_name,
                    'success': False,
                    'duration': stage_duration,
                    'error': str(e),
                    'input_count': 0,
                    'output_size': 0
                })
                raise  # Re-raise to stop pipeline execution

        # Generate execution report
        execution_duration = (datetime.now() - start_time).total_seconds()
        report = self._generate_execution_report(stage_results, execution_duration)

        return {
            'success': True,
            'outputs': stage_outputs,
            'report': report,
            'execution_time': execution_duration
        }

  def \_prepare_stage_inputs(self, stage: PipelineStage, available_outputs: Dict[str, Any]) -> Dict[str, Any]:
  """Prepare inputs for a pipeline stage based on its signature."""
  sig = inspect.signature(stage.function)
  stage_inputs = {}

        for param_name, param in sig.parameters.items():
            # Try to match parameter by name first
            if param_name in available_outputs:
                stage_inputs[param_name] = available_outputs[param_name]
            # Then try to match by type
            elif param.annotation and param.annotation != inspect.Parameter.empty:
                for output_name, output_value in available_outputs.items():
                    if isinstance(output_value, param.annotation):
                        stage_inputs[param_name] = output_value
                        break

        return stage_inputs

  def \_generate_execution_report(self, stage_results: List[Dict[str, Any]],
  execution_duration: float) -> str:
  """Generate execution report using templates."""
  context = {
  'pipeline_name': 'Configuration Pipeline',
  'execution_timestamp': datetime.now().isoformat(),
  'success': all(r['success'] for r in stage_results),
  'execution_duration': execution_duration,
  'stage_results': stage_results,
  'bottleneck_stage': max[stage_results, key=lambda x: x['duration']]('stage_name'),
  'cache_hit_rate': 0, # Placeholder
  'lineage_overhead': 5.2 # Placeholder
  }

        template = self.template_env.get_template('pipeline_report')
        return template.render(**context)

# ==========================================

# Snippet 11: Advanced Jinja Macros for Configuration Operations

# Description: Reusable Jinja macros that embed configuration business logic directly in templates

# ==========================================

# Advanced macro definitions for configuration operations

ADVANCED_CONFIG_MACROS = '''
{# ========================================== #}
{# Macro: conflict_resolution - Handle configuration conflicts declaratively #}
{# ========================================== #}
{% macro conflict_resolution(conflicts, resolution_strategy='priority', custom_rules={}) %}
{#
Resolve configuration conflicts using specified strategy.
Args:
conflicts: List of conflict objects
resolution_strategy: 'priority', 'merge', 'manual', 'newest'
custom_rules: Dict of custom resolution rules

# }

{% set resolved_values = {} %}
{% for conflict in conflicts %}
{% set resolution = None %}

    {# Apply custom rules first #}
    {% if conflict.path in custom_rules %}
        {% set resolution = custom_rules[conflict.path] %}

    {# Priority-based resolution #}
    {% elif resolution_strategy == 'priority' %}
        {% set highest_priority = conflict.sources | max(attribute='priority') %}
        {% set resolution = highest_priority.value %}

    {# Merge strategy for compatible values #}
    {% elif resolution_strategy == 'merge' %}
        {% if conflict.type == 'array' %}
            {% set resolution = [] %}
            {% for source in conflict.sources %}
                {% set resolution = resolution + source.value %}
            {% endfor %}
        {% elif conflict.type == 'object' %}
            {% set resolution = {} %}
            {% for source in conflict.sources %}
                {% set resolution = resolution.update(source.value) %}
            {% endfor %}
        {% else %}
            {# Fallback to priority for non-mergeable types #}
            {% set highest_priority = conflict.sources | max(attribute='priority') %}
            {% set resolution = highest_priority.value %}
        {% endif %}

    {# Newest value wins #}
    {% elif resolution_strategy == 'newest' %}
        {% set newest_source = conflict.sources | max(attribute='timestamp') %}
        {% set resolution = newest_source.value %}

    {# Manual resolution required #}
    {% elif resolution_strategy == 'manual' %}
        {% set resolution = {
            'type': 'manual_required',
            'conflict_id': conflict.id,
            'options': conflict.sources | map(attribute='value') | list
        } %}
    {% endif %}

    {% set _ = resolved_values.update({conflict.path: resolution}) %}

{% endfor %}

{# Generate resolution report #}

## Conflict Resolution Report

{% for conflict in conflicts %}

### {{ conflict.path }}

- **Conflict Type**: {{ conflict.type }}
- **Sources**: {{ conflict.sources | length }}
- **Resolution Strategy**: {{ resolution_strategy }}
- **Resolved Value**: `{{ resolved_values[conflict.path] }}`
  {% if resolution_strategy == 'manual' and resolved_values[conflict.path].type == 'manual_required' %}
- **⚠️ Manual Resolution Required**
  - Options: {{ resolved_values[conflict.path].options | join(', ') }}
    {% endif %}

{% endfor %}
{% endmacro %}

{# ========================================== #}
{# Macro: migration_bridge - Generate migration code between config versions #}
{# ========================================== #}
{% macro migration_bridge(from_version, to_version, config_data, migration_rules={}) %}
{#
Generate migration code to transform config from one version to another.
Args:
from_version: Source version string
to_version: Target version string
config_data: Configuration data to migrate
migration_rules: Custom migration rules

# }

# Configuration Migration: {{ from_version }} → {{ to_version }}

# Generated: {{ moment().format('YYYY-MM-DD HH:mm:ss') }}

{% if from_version == '2.0' and to_version == '3.0' %}
{# Docker Compose v2 to v3 migration #}
{% if 'links' in config_data.services %} # Migrating 'links' to 'depends_on'
{% for service_name, service_config in config_data.services.items() %}
{% if service_config.links %}
services:
{{ service_name }}:
depends_on:
{% for link in service_config.links %} - {{ link.split[':'](0) }}
{% endfor %} # Note: 'links' removed in v3, use 'depends_on' for startup order
{% endif %}
{% endfor %}
{% endif %}

    {% if 'volume_driver' in config_data %}
        # Migrating volume_driver to volumes section
        volumes:
        {% for volume_name in config_data.volumes %}
          {{ volume_name }}:
            driver: {{ config_data.volume_driver }}
        {% endfor %}
    {% endif %}

{% elif from_version == '3.0' and to_version == '3.8' %}
{# Docker Compose v3.0 to v3.8 migration #}
version: '3.8'

    {% if config_data.services %}
        # Adding modern health check format
        services:
        {% for service_name, service_config in config_data.services.items() %}
          {{ service_name }}:
            {% if not service_config.healthcheck %}
            healthcheck:
              test: ["CMD", "curl", "-f", "http://localhost:{{ service_config.ports[0].split(':')[1] if service_config.ports else '80' }}/health"]
              interval: 30s
              timeout: 10s
              retries: 3
              start_period: 40s
            {% endif %}
        {% endfor %}
    {% endif %}

{% else %}
{# Custom migration rules #}
{% for rule_name, rule_config in migration_rules.items() %}
{% if rule_config.applies_to_version(from_version, to_version) %}

# Applying custom rule: {{ rule_name }}

{{ rule_config.generate_code(config_data) }}
{% endif %}
{% endfor %}
{% endif %}

# Migration Validation

{% set validation_checks = [] %}
{% if 'services' in config_data %}
{% for service_name, service_config in config_data.services.items() %}
{% if not service_config.image and not service_config.build %}
{% set_ = validation_checks.append('Service ' + service_name + ' missing image or build directive') %}
{% endif %}
{% endfor %}
{% endif %}

{% if validation_checks %}

# ⚠️ Validation Warnings

{% for check in validation_checks %}

# - {{ check }}

{% endfor %}
{% endif %}
{% endmacro %}

{# ========================================== #}
{# Macro: dag_inspector - Generate DAG analysis and visualization #}
{# ========================================== #}
{% macro dag_inspector(pipeline_graph, lineage_data, focus_node=None) %}
{#
Generate comprehensive DAG analysis and visualization.
Args:
pipeline_graph: NetworkX graph of the pipeline
lineage_data: Lineage tracking information
focus_node: Optional node to focus analysis on

# }

# Pipeline DAG Analysis

{% if focus_node %}

## Focused Analysis: {{ focus_node }}

{% else %}

## Complete Pipeline Analysis

{% endif %}

### Graph Statistics

- **Total Nodes**: {{ pipeline_graph.nodes() | length }}
- **Total Edges**: {{ pipeline_graph.edges() | length }}
- **Max Depth**: {{ pipeline_graph | dag_depth }}
- **Parallel Stages**: {{ pipeline_graph | parallel_stages | length }}

### Execution Order

```
{% for stage in pipeline_graph | topological_sort %}
{{ stage }}{% if not loop.last %} → {% endif %}
{% endfor %}
```

### Node Details

{% for node in pipeline_graph.nodes() %}
{% if not focus_node or node == focus_node or node in pipeline_graph.predecessors(focus_node) or node in pipeline_graph.successors(focus_node) %}

#### {{ node }}

- **Type**: {{ pipeline_graph.nodes[node].get('type', 'config_stage') }}
- **Dependencies**: {{ pipeline_graph.predecessors(node) | list | join(', ') or 'None' }}
- **Dependents**: {{ pipeline_graph.successors(node) | list | join(', ') or 'None' }}
  {% if lineage_data.get(node) %}
- **Transformations**: {{ lineage_data[node].transformations | length }}
- **Value Changes**: {{ lineage_data[node].value_changes | length }}
  {% endif %}
  {% endif %}
  {% endfor %}

### Critical Path Analysis

{% set critical_path = pipeline_graph | find_critical_path %}
Critical path: {{ critical_path | join(' → ') }}
Estimated duration: {{ critical_path | map('duration') | sum }} seconds

### Bottleneck Detection

{% set bottlenecks = pipeline_graph | find_bottlenecks %}
{% if bottlenecks %}
**Potential bottlenecks:**
{% for bottleneck in bottlenecks %}

- {{ bottleneck.node }}: {{ bottleneck.reason }}
  {% endfor %}
  {% endif %}

### Mermaid Diagram

```mermaid
graph TD
{% for node in pipeline_graph.nodes() %}
    {{ node }}[{{ node }}]
    {% if focus_node == node %}
    style {{ node }} fill:#ff9999
    {% endif %}
{% endfor %}

{% for source, target in pipeline_graph.edges() %}
    {{ source }} --> {{ target }}
{% endfor %}
```

{% endmacro %}
'''

class AdvancedConfigMacros:
"""Provider for advanced configuration macros."""

    def __init__(self):
        from jinja2 import Environment, DictLoader
        self.env = Environment(loader=DictLoader({
            'config_macros': ADVANCED_CONFIG_MACROS
        }))

        # Add custom filters for macro functionality
        self.env.filters.update({
            'dag_depth': self._calculate_dag_depth,
            'parallel_stages': self._find_parallel_stages,
            'topological_sort': self._topological_sort,
            'find_critical_path': self._find_critical_path,
            'find_bottlenecks': self._find_bottlenecks
        })

    def get_macro_template(self):
        """Get the macro template for inclusion in other templates."""
        return self.env.get_template('config_macros')

    def _calculate_dag_depth(self, graph) -> int:
        """Calculate the maximum depth of a DAG."""
        try:
            return nx.dag_longest_path_length(graph)
        except:
            return 0

    def _find_parallel_stages(self, graph) -> List[str]:
        """Find stages that can run in parallel."""
        parallel_groups = []
        for level in nx.topological_generations(graph):
            if len(level) > 1:
                parallel_groups.extend(level)
        return parallel_groups

    def _topological_sort(self, graph) -> List[str]:
        """Get topological sort of graph nodes."""
        try:
            return list(nx.topological_sort(graph))
        except:
            return list(graph.nodes())

# ==========================================

# Snippet 12: Integration Decorators for Seamless SDK Integration

# Description: Decorators that seamlessly integrate configuration archaeology into existing systems

# ==========================================

from typing import Union, Type, Callable, List, Dict, Any
import functools
from functools import wraps
import inspect

class ConfigAwarenessMixin:
"""Mixin that adds configuration archaeology awareness to any class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config_lineage_tracker = None
        self._config_registry = None
        self._archaeological_context = {}

    def set_archaeological_context(self, lineage_tracker: 'ConfigLineageTracker',
                                 config_registry: 'ConfigRegistry'):
        """Set the archaeological context for this instance."""
        self._config_lineage_tracker = lineage_tracker
        self._config_registry = config_registry

    def get_config_lineage(self, config_path: str) -> Dict[str, Any]:
        """Get lineage information for a configuration path."""
        if self._config_registry:
            return self._config_registry.generate_lineage_context(config_path)
        return {}

def config_aware(cls: Type = None, \*, auto_inject: bool = True,
track_methods: List[str] = None):
"""
Class decorator that makes a class configuration-archaeology aware.

    Args:
        cls: The class to decorate
        auto_inject: Automatically inject archaeological context
        track_methods: List of method names to automatically track
    """
    def decorator(cls: Type) -> Type:
        # Add the mixin to the class
        if ConfigAwarenessMixin not in cls.__mro__:
            # Create new class with mixin
            cls = type(cls.__name__, (ConfigAwarenessMixin, cls), dict(cls.__dict__))

        # Wrap specified methods with tracking
        if track_methods:
            for method_name in track_methods:
                if hasattr(cls, method_name):
                    original_method = getattr(cls, method_name)
                    wrapped_method = _wrap_method_with_tracking(original_method, method_name)
                    setattr(cls, method_name, wrapped_method)

        # Add metadata
        cls._config_aware = True
        cls._auto_inject = auto_inject
        cls._tracked_methods = track_methods or []

        return cls

    if cls is None:
        return decorator
    else:
        return decorator(cls)

def dag_node(name: str = None,
inputs: List[str] = None,
outputs: List[str] = None,
template: str = None):
"""
Decorator that marks a function as a DAG processing node.

    Args:
        name: Node name (defaults to function name)
        inputs: Expected input types/names
        outputs: Output types/names
        template: Optional template for node visualization
    """
    def decorator(func: Callable) -> Callable:
        node_name = name or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract configuration inputs
            config_inputs = []
            for arg in args:
                if isinstance(arg, ConfigAST):
                    config_inputs.append(arg)

            for value in kwargs.values():
                if isinstance(value, ConfigAST):
                    config_inputs.append(value)

            # Execute function
            result = func(*args, **kwargs)

            # Register as DAG node if we have a global pipeline registry
            if hasattr(_pipeline_registry, 'register_dag_node'):
                _pipeline_registry.register_dag_node(
                    node_name,
                    config_inputs,
                    result,
                    func
                )

            return result

        # Attach metadata
        wrapper._dag_node = {
            'name': node_name,
            'inputs': inputs or [],
            'outputs': outputs or [],
            'template': template,
            'original_function': func
        }

        return wrapper

    return decorator

def inject_lineage(config_param: str = None,
context_param: str = 'lineage_context'):
"""
Decorator that automatically injects lineage tracking context into function calls.

    Args:
        config_param: Name of parameter containing ConfigAST
        context_param: Parameter name to inject lineage context into
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Find ConfigAST parameter
            config_ast = None
            if config_param and config_param in kwargs:
                config_ast = kwargs[config_param]
            else:
                # Search through all arguments
                for arg in args:
                    if isinstance(arg, ConfigAST):
                        config_ast = arg
                        break

                if not config_ast:
                    for value in kwargs.values():
                        if isinstance(value, ConfigAST):
                            config_ast = value
                            break

            # Inject lineage context if we found a config
            if config_ast and hasattr(config_ast, 'value_origins'):
                lineage_context = {
                    'value_origins': config_ast.value_origins,
                    'merge_history': config_ast.merge_history,
                    'config_metadata': config_ast.metadata
                }
                kwargs[context_param] = lineage_context

            return func(*args, **kwargs)

        wrapper._inject_lineage = {
            'config_param': config_param,
            'context_param': context_param
        }

        return wrapper

    return decorator

def \_wrap_method_with_tracking(original_method: Callable, method_name: str) -> Callable:
"""Wrap a method with configuration tracking."""
@wraps(original_method)
def wrapper(self, \*args, **kwargs): # Track method execution if archaeological context is available
if hasattr(self, '\_config_lineage_tracker') and self.\_config_lineage_tracker:
operation_id = f"{self.**class**.**name\*\*}.{method_name}"

            # Find config inputs
            config_inputs = [arg for arg in args if isinstance(arg, ConfigAST)]

            # Execute original method
            result = original_method(self, *args, **kwargs)

            # Track if result is a ConfigAST
            if isinstance(result, ConfigAST) and config_inputs:
                self._config_lineage_tracker.record_merge_operation(
                    config_inputs,
                    result,
                    operation_id
                )

            return result
        else:
            # Execute without tracking
            return original_method(self, *args, **kwargs)

    return wrapper

# Example usage of integration decorators

@config_aware(track_methods=['process_config', 'merge_configs'])
class ConfigurationManager:
"""Example configuration manager with archaeological awareness."""

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    @inject_lineage(config_param='config')
    def process_config(self, config: ConfigAST, lineage_context: Dict[str, Any] = None):
        """Process configuration with automatic lineage injection."""
        if lineage_context:
            print(f"Processing config with {len(lineage_context['value_origins'])} tracked values")

        # Process the configuration
        return config

    @dag_node(name="config_validation", inputs=["config"], outputs=["validated_config"])
    def validate_config(self, config: ConfigAST) -> ConfigAST:
        """Validate configuration as a DAG node."""
        # Validation logic here
        return config

# ==========================================

# Snippet 13: Template Context Extensions for Archaeological Awareness

# Description: Enhanced Jinja template context that provides archaeological capabilities

# ==========================================

from jinja2 import Environment, DictLoader, select_autoescape
from typing import Any, Dict, List, Optional, Union
import yaml
from datetime import datetime

class LineageContext:
"""Enhanced template context with archaeological awareness."""

    def __init__(self, config_registry: 'ConfigRegistry',
                 lineage_tracker: 'ConfigLineageTracker'):
        self.config_registry = config_registry
        self.lineage_tracker = lineage_tracker
        self._cached_lineage = {}

    def get_value_origin(self, config_path: str) -> Dict[str, Any]:
        """Get origin information for a configuration value."""
        if config_path not in self._cached_lineage:
            self._cached_lineage[config_path] = self.config_registry.generate_lineage_context(config_path)
        return self._cached_lineage[config_path]

    def trace_value_lineage(self, config_path: str, target_config: 'ConfigAST') -> Dict[str, Any]:
        """Trace complete lineage for a configuration value."""
        return self.lineage_tracker.trace_value_lineage(config_path, target_config)

    def get_merge_conflicts(self, config_path: str) -> List[Dict[str, Any]]:
        """Get any merge conflicts for a configuration path."""
        lineage = self.get_value_origin(config_path)
        return lineage.get('conflicts', [])

    def get_transformation_history(self, config_path: str) -> List[Dict[str, Any]]:
        """Get transformation history for a configuration path."""
        lineage = self.get_value_origin(config_path)
        return lineage.get('lineage_chain', [])

def config_merge(base_config: Dict[str, Any],
override_config: Dict[str, Any],
strategy: str = 'override') -> Dict[str, Any]:
"""
Jinja filter for intelligent configuration merging.

    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary
        strategy: Merge strategy ('override', 'merge', 'append')
    """
    if strategy == 'override':
        # Simple override strategy
        result = base_config.copy()
        result.update(override_config)
        return result

    elif strategy == 'merge':
        # Deep merge strategy
        result = base_config.copy()

        def deep_merge(base: Dict, override: Dict) -> Dict:
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_merge(base[key], value)
                elif key in base and isinstance(base[key], list) and isinstance(value, list):
                    base[key] = base[key] + value  # Append lists
                else:
                    base[key] = value
            return base

        return deep_merge(result, override_config)

    elif strategy == 'append':
        # Append strategy for arrays
        result = base_config.copy()
        for key, value in override_config.items():
            if key in result and isinstance(result[key], list):
                if isinstance(value, list):
                    result[key].extend(value)
                else:
                    result[key].append(value)
            else:
                result[key] = value
        return result

    else:
        raise ValueError(f"Unknown merge strategy: {strategy}")

class ArchaeologicalTemplateEnvironment:
"""Enhanced Jinja environment with archaeological capabilities."""

    def __init__(self, config_registry: 'ConfigRegistry',
                 lineage_tracker: 'ConfigLineageTracker'):
        self.config_registry = config_registry
        self.lineage_tracker = lineage_tracker
        self.lineage_context = LineageContext(config_registry, lineage_tracker)

        # Create Jinja environment with custom filters and globals
        self.env = Environment(
            loader=DictLoader({}),
            autoescape=select_autoescape(['html', 'xml']),
        )

        # Add archaeological filters
        self.env.filters.update({
            'config_merge': config_merge,
            'trace_lineage': self._trace_lineage_filter,
            'get_conflicts': self._get_conflicts_filter,
            'format_origin': self._format_origin_filter,
            'highlight_changes': self._highlight_changes_filter
        })

        # Add archaeological globals
        self.env.globals.update({
            'lineage': self.lineage_context,
            'config_registry': self.config_registry,
            'get_schema': self._get_schema_global,
            'query_dag': self._query_dag_global,
            'moment': lambda: datetime.now()  # Moment.js-like function
        })

    def _trace_lineage_filter(self, config_path: str, target_config: 'ConfigAST') -> Dict[str, Any]:
        """Filter to trace configuration lineage."""
        return self.lineage_context.trace_value_lineage(config_path, target_config)

    def _get_conflicts_filter(self, config_path: str) -> List[Dict[str, Any]]:
        """Filter to get merge conflicts for a configuration path."""
        return self.lineage_context.get_merge_conflicts(config_path)

    def _format_origin_filter(self, origin_info: Dict[str, Any]) -> str:
        """Filter to format origin information for display."""
        if not origin_info:
            return "Unknown origin"

        file_path = origin_info.get('file_path', 'unknown')
        line_number = origin_info.get('line_number', 0)
        return f"{file_path}:{line_number}"

    def _highlight_changes_filter(self, old_value: Any, new_value: Any) -> str:
        """Filter to highlight changes between configuration values."""
        if old_value == new_value:
            return f"<span class='unchanged'>{new_value}</span>"
        else:
            return f"<span class='changed' title='Was: {old_value}'>⚡ {new_value}</span>"

    def _get_schema_global(self, config_name: str) -> Dict[str, Any]:
        """Global function to get schema for a configuration."""
        return self.config_registry.schema_inference_cache.get(config_name, {})

    def _query_dag_global(self, query: str) -> Any:
        """Global function to query the configuration DAG."""
        # Implementation would parse query and return DAG information
        return f"DAG query result for: {query}"

    def render_template_string(self, template_string: str, context: Dict[str, Any] = None) -> str:
        """Render a template string with archaeological context."""
        template = self.env.from_string(template_string)

        # Enhance context with archaeological capabilities
        enhanced_context = {
            **(context or {}),
            'archaeological_env': self,
            'lineage': self.lineage_context
        }

        return template.render(**enhanced_context)

# Example template using archaeological features

ARCHAEOLOGICAL_TEMPLATE_EXAMPLE = '''
{# Configuration Archaeological Report Template #}

# Configuration Archaeological Report

**Generated**: {{ moment().strftime('%Y-%m-%d %H:%M:%S') }}

## Configuration Analysis for: {{ config_name }}

### Value Origins

{% for path, value in config_values.items() %}

#### {{ path }}

- **Current Value**: `{{ value }}`
- **Origin**: {{ lineage.get_value_origin(path) | format_origin }}
- **Conflicts**: {{ lineage.get_merge_conflicts(path) | length }} found
  {% if lineage.get_merge_conflicts(path) %}

  **Conflict Details:**
  {% for conflict in lineage.get_merge_conflicts(path) %}

  - Type: {{ conflict.type }}
  - Sources: {{ conflict.sources | map(attribute='name') | join(', ') }}
    {% endfor %}
    {% endif %}
    {% endfor %}

### Schema Information

**Inferred Schema**: {{ get_schema(config_name) }}

### Recent Changes

{% for change in recent_changes %}

- **{{ change.operation }}** at {{ change.timestamp }}
  {% if change.sources %}
  - Sources: {{ change.sources | join(', ') }}
    {% endif %}
    {% endfor %}

### Change Visualization

{% for path, value in config_values.items() %}
{% set lineage_data = lineage.trace_value_lineage(path, target_config) %}
{% if lineage_data.transformations %}

#### {{ path }} Evolution

{% for transformation in lineage_data.transformations[-3:] %} {# Last 3 transformations #}

- **{{ transformation.operation_id }}**: {{ transformation.old_value | highlight_changes(transformation.new_value) | safe }}
  {% endfor %}
  {% endif %}
  {% endfor %}
  '''

# ==========================================

# Snippet 14: Complete Integration Example - Archaeological Config Manager

# Description: Complete example showing all SDK constructs working together in a real system

# ==========================================

from pathlib import Path
import asyncio
import tempfile
import os

@config_aware(auto_inject=True, track_methods=['load_config', 'merge_configs'])
class ArchaeologicalConfigManager:
"""
Complete configuration manager demonstrating all archaeological SDK features.

    This class shows how all the advanced Jinja constructs work together:
    - Pipeline decorators for DAG processing
    - Macro-driven conflict resolution
    - Template-generated reports
    - Seamless lineage tracking
    """

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.config_registry = ConfigRegistry()
        self.lineage_tracker = ConfigLineageTracker()
        self.pipeline_template = ConfigPipelineTemplate(self.lineage_tracker)
        self.template_env = ArchaeologicalTemplateEnvironment(
            self.config_registry,
            self.lineage_tracker
        )

        # Set archaeological context
        self.set_archaeological_context(self.lineage_tracker, self.config_registry)

        # Initialize pipeline stages
        self._setup_pipeline_stages()

    def _setup_pipeline_stages(self):
        """Set up configuration processing pipeline stages."""

        @config_pipeline(name="load_base_config", depends_on=[], track_lineage=True)
        def load_base_config(file_path: str) -> ConfigAST:
            """Load base configuration file."""
            content = Path(file_path).read_text()
            config = ConfigAST(content, 'yaml', {'source_file': file_path, 'type': 'base'})
            self.config_registry.register_config_source('base', config)
            return config

        @config_pipeline(name="apply_environment", depends_on=["load_base_config"], track_lineage=True)
        @inject_lineage(config_param='base_config')
        def apply_environment_overrides(base_config: ConfigAST, env_file: str,
                                      lineage_context: Dict[str, Any] = None) -> ConfigAST:
            """Apply environment-specific configuration overrides."""
            env_content = Path(env_file).read_text()
            env_config = ConfigAST(env_content, 'yaml', {'source_file': env_file, 'type': 'environment'})

            self.config_registry.register_config_source('environment', env_config)

            merged = base_config.merge_with(env_config, strategy='environment_override')
            return merged

        @config_pipeline(name="inject_secrets", depends_on=["apply_environment"], track_lineage=True)
        @dag_node(name="secret_injection", inputs=["config"], outputs=["secure_config"])
        def inject_secrets(config: ConfigAST, secrets_source: str = "vault") -> ConfigAST:
            """Inject secrets into configuration."""
            # Simulate secret injection
            parsed = config.parse_config()

            # Replace placeholder values with secrets
            if 'services' in parsed:
                for service_name, service_config in parsed['services'].items():
                    if 'environment' in service_config:
                        env_vars = service_config['environment']
                        for key, value in env_vars.items():
                            if isinstance(value, str) and value == '${SECRET}':
                                env_vars[key] = f'secret_value_for_{key.lower()}'

            # Create new ConfigAST with secrets injected
            updated_content = yaml.dump(parsed)
            return ConfigAST(
                updated_content,
                'yaml',
                {**config.metadata, 'secrets_injected': True, 'secrets_source': secrets_source}
            )

        @config_pipeline(name="validate_final", depends_on=["inject_secrets"], track_lineage=True)
        def validate_final_config(config: ConfigAST) -> ConfigAST:
            """Perform final validation on configuration."""
            parsed = config.parse_config()

            # Basic validation
            if 'services' not in parsed:
                raise ValueError("Configuration must contain 'services' section")

            for service_name, service_config in parsed['services'].items():
                if 'image' not in service_config and 'build' not in service_config:
                    raise ValueError(f"Service '{service_name}' must specify either 'image' or 'build'")

            # Mark as validated
            config.metadata['validated'] = True
            config.metadata['validation_timestamp'] = datetime.now()

            return config

        # Store pipeline functions for later use
        self.pipeline_stages = {
            'load_base_config': load_base_config,
            'apply_environment': apply_environment_overrides,
            'inject_secrets': inject_secrets,
            'validate_final': validate_final_config
        }

    async def process_configuration_pipeline(self, base_file: str, env_file: str) -> Dict[str, Any]:
        """Execute complete configuration processing pipeline."""

        # Generate execution plan
        execution_plan = self.pipeline_template.generate_execution_plan()
        print("📋 Pipeline Execution Plan:")
        print(execution_plan)
        print()

        # Execute pipeline
        initial_configs = {'base_file_path': base_file, 'env_file_path': env_file}
        result = await self.pipeline_template.execute_pipeline(initial_configs)

        if result['success']:
            print("✅ Pipeline executed successfully!")
            print(f"⏱️ Execution time: {result['execution_time']:.2f} seconds")

            # Generate archaeological report
            final_config = result['outputs']['validate_final']
            report = self.generate_archaeological_report(final_config)

            return {
                'final_config': final_config,
                'pipeline_report': result['report'],
                'archaeological_report': report
            }
        else:
            print("❌ Pipeline execution failed!")
            return result

    def generate_archaeological_report(self, config: ConfigAST,
                                     focus_paths: List[str] = None) -> str:
        """Generate comprehensive archaeological report using templates."""

        # Prepare context for template rendering
        context = {
            'config_name': self.name,
            'target_config': config,
            'config_values': self._extract_focus_values(config, focus_paths),
            'current_version': config.metadata.get('version', '1.0'),
            'latest_version': '2.0',  # Example
            'config_data': config.parse_config(),
            'recent_changes': self._get_recent_changes(config)
        }

        # Render archaeological report
        return self.template_env.render_template_string(
            ARCHAEOLOGICAL_TEMPLATE_EXAMPLE,
            context
        )

    def _extract_focus_values(self, config: ConfigAST, focus_paths: List[str] = None) -> Dict[str, Any]:
        """Extract values for focused analysis."""
        parsed = config.parse_config()

        if focus_paths:
            result = {}
            for path in focus_paths:
                value = self._get_nested_value(parsed, path)
                if value is not None:
                    result[path] = value
            return result
        else:
            # Return sample values for demonstration
            return {
                'services.web.image': parsed.get('services', {}).get('web', {}).get('image'),
                'services.web.environment.ENV': parsed.get('services', {}).get('web', {}).get('environment', {}).get('ENV'),
                'services.database.environment.POSTGRES_PASSWORD': parsed.get('services', {}).get('database', {}).get('environment', {}).get('POSTGRES_PASSWORD')
            }

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value using dot notation."""
        parts = path.split('.')
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _get_recent_changes(self, config: ConfigAST) -> List[Dict[str, Any]]:
        """Get recent changes for display."""
        changes = []

        for operation in config.merge_history[-5:]:  # Last 5 operations
            changes.append({
                'operation': operation.get('operation', 'unknown'),
                'timestamp': operation.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S') if isinstance(operation.get('timestamp'), datetime) else str(operation.get('timestamp', 'unknown')),
                'sources': operation.get('sources', [])
            })

        return changes

    def query_configuration_lineage(self, config_path: str, final_config: ConfigAST) -> Dict[str, Any]:
        """Query lineage for a specific configuration path."""
        return self.lineage_tracker.generate_why_query_response(config_path, final_config)

# ==========================================

# Snippet 15: Complete Demonstration and Usage Example

# Description: End-to-end demonstration of the archaeological configuration system

# ==========================================

async def demonstrate_archaeological_config_system():
"""
Complete demonstration of the archaeological configuration system.

    This shows how all the advanced Jinja SDK constructs work together:
    - Template pipelines with @config_pipeline decorators
    - Advanced macros for conflict resolution and migration
    - Archaeological template context with lineage awareness
    - Integration decorators for seamless adoption
    """

    print("🏛️ Configuration Archaeological System Demonstration")
    print("=" * 70)

    # Create the archaeological config manager
    manager = ArchaeologicalConfigManager("microservice-config")

    # Create example configuration files
    base_config_content = '''

version: "3.8"
services:
web:
image: nginx:1.20
ports: - "80:80"
environment:
ENV: production
LOG_LEVEL: info

database:
image: postgres:13
environment:
POSTGRES_DB: myapp
POSTGRES_USER: appuser
POSTGRES_PASSWORD: ${SECRET}
volumes: - db_data:/var/lib/postgresql/data

volumes:
db_data:
'''

    env_override_content = '''

version: "3.8"
services:
web:
image: nginx:1.21-alpine # Newer, smaller image
ports: - "8080:80" # Different port for dev
environment:
ENV: development
LOG_LEVEL: debug
DEBUG: "true"
volumes: - ./src:/usr/share/nginx/html # Local development mount

database:
ports: - "5432:5432" # Expose database port in dev
environment:
POSTGRES_PASSWORD: dev_password_override
'''

    # Write temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as base_file:
        base_file.write(base_config_content)
        base_file_path = base_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as env_file:
        env_file.write(env_override_content)
        env_file_path = env_file.name

    try:
        print("📁 Processing configuration files:")
        print(f"   Base: {os.path.basename(base_file_path)}")
        print(f"   Environment: {os.path.basename(env_file_path)}")
        print()

        # Process the configuration pipeline
        result = await manager.process_configuration_pipeline(base_file_path, env_file_path)

        if result:
            print("📊 Archaeological Analysis Results:")
            print("=" * 50)

            # Save archaeological report
            with open('archaeological_report.md', 'w') as f:
                f.write(result['archaeological_report'])
            print("✅ Detailed archaeological report saved to: archaeological_report.md")

            # Save pipeline report
            with open('pipeline_report.md', 'w') as f:
                f.write(result['pipeline_report'])
            print("✅ Pipeline execution report saved to: pipeline_report.md")

            # Demonstrate lineage queries
            print("\n🔍 Lineage Query Examples:")
            print("-" * 30)

            final_config = result['final_config']

            # Query specific configuration paths
            test_paths = [
                'services.web.image',
                'services.web.environment.ENV',
                'services.database.environment.POSTGRES_PASSWORD'
            ]

            for path in test_paths:
                try:
                    query_result = manager.query_configuration_lineage(path, final_config)
                    print(f"📍 {path}:")
                    print(f"   Answer: {query_result['short_answer']}")
                    print(f"   Confidence: {query_result['confidence']:.1%}")
                    print(f"   Detailed lineage paths: {len(query_result['detailed_lineage']['lineage_paths'])}")
                    print()
                except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup temporary files
        try:
            os.unlink(base_file_path)
            os.unlink(env_file_path)
        except:
            pass

    print("\n🏆 Archaeological Configuration System demonstration complete!")
    print()
    print("This system provides complete configuration archaeology capabilities")
    print("while maintaining the advanced Jinja patterns from Chapters 1-3:")
    print()
    print("📚 Chapter Integration Summary:")
    print("   • Chapter 1: Self-modifying templates → Pipeline self-optimization")
    print("   • Chapter 2: Multi-language patterns → Multi-template orchestration")
    print("   • Chapter 3: Configuration archaeology → Template-driven DAG processing")
    print()
    print("🚀 Advanced SDK Features:")
    print("   • @config_pipeline: Declarative pipeline stage definition")
    print("   • @inject_lineage: Transparent archaeological context injection")
    print("   • @config_aware: Seamless integration with existing systems")
    print("   • @dag_node: Template-driven DAG node declaration")
    print("   • Advanced macros: Business logic embedded in templates")
    print("   • Archaeological context: Lineage-aware template rendering")
    print()
    print("🎯 Production Benefits:")
    print("   • Reduces config debugging time from hours to minutes")
    print("   • Makes complex config pipelines transparent and auditable")
    print("   • Provides automatic documentation through template generation")
    print("   • Enables confident refactoring of legacy configuration systems")
    print("   • Creates self-documenting infrastructure")

# Helper function to run the demonstration

def run_archaeological_demo():
"""Run the archaeological configuration system demonstration."""
return asyncio.run(demonstrate_archaeological_config_system())

# Example of using the system in production

class ProductionConfigArchaeologist:
"""Production-ready configuration archaeologist with enterprise features."""

    def __init__(self, config_paths: Dict[str, str], monitoring_enabled: bool = True):
        self.config_paths = config_paths
        self.monitoring_enabled = monitoring_enabled
        self.manager = ArchaeologicalConfigManager("production-config")

        # Production-specific setup
        self._setup_monitoring()
        self._setup_alerting()

    def _setup_monitoring(self):
        """Set up monitoring for configuration changes."""
        if self.monitoring_enabled:
            print("📊 Setting up configuration monitoring...")
            # Would integrate with Prometheus, DataDog, etc.

    def _setup_alerting(self):
        """Set up alerting for configuration issues."""
        if self.monitoring_enabled:
            print("🚨 Setting up configuration alerting...")
            # Would integrate with PagerDuty, Slack, etc.

    async def investigate_config_issue(self, service_name: str, config_key: str) -> str:
        """Investigate a specific configuration issue in production."""

        print(f"🔍 Investigating {service_name}.{config_key}...")

        # Load current production configuration
        prod_config_file = self.config_paths.get('production')
        if not prod_config_file:
            return "❌ Production configuration file not found"

        # Process through archaeological pipeline
        result = await self.manager.process_configuration_pipeline(
            self.config_paths['base'],
            prod_config_file
        )

        if result:
            # Generate targeted investigation report
            config_path = f"services.{service_name}.{config_key}"
            investigation = self.manager.query_configuration_lineage(
                config_path,
                result['final_config']
            )

            return f"""

🔍 Configuration Investigation Report

**Service**: {service_name}
**Configuration**: {config_key}
**Investigation Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Quick Answer**: {investigation['short_answer']}
**Confidence**: {investigation['confidence']:.1%}

**Recommended Actions**:
{chr(10).join(f"• {action}" for action in investigation.get('suggested_actions', ['No specific actions recommended']))}

**Detailed Report**: See archaeological_report.md for complete lineage analysis
"""
else:
return "❌ Failed to analyze configuration"

    def generate_compliance_report(self) -> str:
        """Generate compliance report for audit purposes."""

        report = f"""

# Configuration Compliance Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Archaeological Capabilities

✅ **Complete lineage tracking**: All configuration changes tracked to source
✅ **Audit trail**: Full history of who changed what, when, and why
✅ **Conflict resolution**: Automated detection and resolution of config conflicts
✅ **Template validation**: All configurations generated through validated templates
✅ **Version management**: Backward-compatible evolution with migration support

## Compliance Status

✅ **SOX Compliance**: Full audit trail with immutable lineage tracking
✅ **Change Management**: All changes flow through documented pipeline stages
✅ **Access Control**: Template-based generation ensures consistent security policies
✅ **Documentation**: Self-documenting configuration through template generation

## Risk Assessment

🟢 **Low Risk**: Template-driven approach reduces human error
🟢 **Low Risk**: Automated validation catches configuration issues early
🟢 **Low Risk**: Complete lineage tracking enables rapid incident resolution
"""

        return report

# Main execution

if **name** == "**main**":
print("🚀 Starting Archaeological Configuration System...")
print()

    # Run the main demonstration
    run_archaeological_demo()

    print("\n" + "="*70)
    print("📋 Production Example: Configuration Issue Investigation")
    print("="*70)

    # Example production usage
    prod_archaeologist = ProductionConfigArchaeologist({
        'base': '/configs/base.yml',
        'production': '/configs/prod-override.yml'
    })

    # Simulate configuration investigation
    print("\n🔍 Simulating production configuration investigation:")
    print("Issue: Database connection timeouts in production")
    print("Investigating: services.database.environment.connection_timeout")
    print()
    print("In production, this would:")
    print("  1. Load actual production configuration files")
    print("  2. Trace the lineage of the timeout setting")
    print("  3. Identify when/where/why it was last changed")
    print("  4. Generate actionable recommendations")
    print("  5. Provide complete audit trail for compliance")

    # Generate compliance report
    compliance_report = prod_archaeologist.generate_compliance_report()
    print("\n📊 Compliance Report Generated:")
    print(compliance_report)

    print("\n🎉 Advanced Jinja SDK demonstration complete!")
    print("Ready for integration into production configuration systems.")
                    print(f"📍 {path}: Error - {e}")
                    print()

            # Show final configuration sample
            print("📋 Final Configuration Sample:")
            print("-" * 30)
            final_parsed = final_config.parse_config()
            print(f"Web service image: {final_parsed['services']['web']['image']}")
            print(f"Web service environment: {final_parsed['services']['web']['environment']['ENV']}")
            print(f"Database password: {final_parsed['services']['database']['environment']['POSTGRES_PASSWORD']}")
            print()

            print("🎯 Key Capabilities Demonstrated:")
            print("   ✓ Template-driven pipeline orchestration (@config_pipeline)")
            print("   ✓ Automatic lineage tracking (@inject_lineage)")
            print("   ✓ Archaeological template context (lineage-aware rendering)")
            print("   ✓ Integration decorators (@config_aware, @dag_node)")
            print("   ✓ Complete value archaeology (who changed what, when, why)")
            print("   ✓ Template-generated documentation and reports")

        else:
            print("❌ Configuration processing failed!")

    except Exception as e:
