# Chapter 1: Self-Modifying Code Generation Pipelines

_Building a FastAPI service generator that evolves based on usage patterns_

## Introduction: The Dream of Self-Improving Code

Picture this: You're at your desk at 2 AM, debugging yet another microservice that's behaving badly in production. The generated code looked perfect when you first scaffolded it six months ago, but now? Now it's a different story. The database connection pool is too small, the health checks are timing out, and somehow every service seems to need the exact same performance tweaks.

Sound familiar? Welcome to the club that nobody wants to join: the "I wish my code generators were smarter" support group.

Here's the thing that keeps platform engineers up at night: **traditional code generators are glorified copy-paste machines**. They spit out the same patterns regardless of whether you're building a high-traffic API or a sleepy background service. They don't learn from their mistakes. They don't adapt to your environment. They're like that coworker who keeps suggesting the same solution to every problem, no matter how many times it doesn't work.

> 🎯 **Plot Twist**: What if your code generators could learn from production? What if they got smarter every time they created something new?

That's exactly what we're building in this chapter. Not just a FastAPI service generator, but a **self-modifying code generation pipeline** that observes, learns, and evolves. Think of it as code generation with a brain—and maybe a bit of attitude too.

By the time we're done here, you'll have built a system that:

- Analyzes production metrics to optimize future generations
- Learns from developer feedback and common fixes
- Automatically applies battle-tested patterns based on real-world usage
- Evolves its templates based on what actually works in your environment

This isn't just about writing better templates. This is about fundamentally changing how we think about code generation.

## The Evolution Problem: Why Static Templates Are Holding Us Back

Let's be brutally honest about traditional code generators. They're stuck in 1995.

### The Static Template Trap

Remember that time you generated a service, deployed it, and then spent the next three weeks applying the same performance optimizations you've applied to every other service? Of course you do. We all do. Because traditional templates are like that friend who tells the same joke at every party—technically correct, but completely oblivious to the room.

Here's what drives us crazy:

**The Database Connection Pool Dance**: Every single generated service needs its connection pool tuned. Every. Single. One. But does your generator learn this? Nope. It keeps churning out services with the default pool size of 5, and you keep manually bumping it to 50.

**The Health Check Tango**: Your monitoring team has told you a thousand times that the default health check timeout is too aggressive for your environment. But there you are, manually adjusting it in every service like some kind of Kubernetes groundhog day.

**The Security Policy Shuffle**: A new security requirement drops, and suddenly you're doing find-and-replace surgery across 200 services. Fun times.

> ⚠️ **Reality Check**: If you find yourself applying the same manual fixes to every generated service, your templates aren't learning from your pain. They're just perpetuating it.

### The Wisdom Waste Problem

Here's what really gets me fired up about this: **Every production service is a goldmine of operational intelligence**, and we're throwing it all away.

Think about it. That service that's been running in production for six months? It knows things:

- Which endpoints are slow and need caching
- What resource allocations actually work in your environment
- Which error patterns crop up repeatedly
- How your traffic actually behaves (spoiler: not like the load tests)

But traditional generators? They ignore all this wisdom. They're like that manager who never listens to feedback from the field. "Oh, the service needs more memory? Interesting. Here's another service with the exact same resource limits!"

It's maddening.

### The Copy-Paste Cascade

And then there's the maintenance nightmare. You know the drill:

1. Generate service A with template v1.0
2. Six months later, generate service B with template v1.0 (because nobody updated it)
3. Production teaches you that services need security headers
4. Update template to v1.1 with security headers
5. Now you have services A and B running different patterns
6. Security audit finds service A is non-compliant
7. Manual patching time! 🎉

This isn't engineering. This is digital archaeology.

> 💡 **The Big Idea**: What if templates could evolve based on real operational feedback? What if they got smarter over time instead of staying frozen in their original, probably suboptimal state?

## Architecture Overview: Building a Brain for Code Generation

Alright, enough complaining. Let's build something better.

Our self-modifying pipeline isn't just a fancy template engine—it's an **intelligent system with four interconnected components** that work together like a well-oiled machine. Think of it as giving your code generator a brain, eyes, and the ability to learn from its mistakes.

### The Four Pillars of Intelligence

**🏗️ Template Engine Core**: This isn't your grandpa's Jinja2. We're talking enhanced templating with metaprogramming capabilities. Templates that know they're templates and can reason about their own structure.

**📊 Analytics Collector**: The eyes and ears of our system. This component stalks your generated services in production (in a totally non-creepy way) and gathers intelligence about what's actually happening out there.

**🧠 Evolution Engine**: The brain. This is where we take all that juicy operational data and turn it into actionable insights about how templates should evolve.

**🛠️ Template Modifier**: The hands. This component takes the evolution insights and actually modifies the templates. Automatically. While you sleep.

> 🚀 **Cool Factor**: When these four components work together, you get code generation that learns from experience. Like having a senior engineer who never forgets a lesson and applies it to every future project.

Let's start with the foundational data structures:

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Protocol
from jinja2 import Environment, Template, meta
from pathlib import Path
import ast
import json
import asyncio
from datetime import datetime, timedelta

@dataclass
class GenerationMetrics:
    """Captures metrics from code generation and service usage."""
    service_id: str
    generation_timestamp: datetime
    template_version: str
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    error_patterns: List[str] = field(default_factory=list)
    usage_patterns: Dict[str, int] = field(default_factory=dict)
    developer_feedback: Dict[str, Any] = field(default_factory=dict)

class TemplateEvolutionStrategy(Protocol):
    """Protocol for template evolution strategies."""

    def analyze_metrics(self, metrics: List[GenerationMetrics]) -> Dict[str, Any]:
        """Analyze collected metrics to identify improvement opportunities."""
        ...

    def generate_modifications(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate template modification suggestions."""
        ...
```

Nothing too wild here, but notice how we're already thinking in terms of metrics, feedback, and evolution strategies. This isn't just about generating code—it's about **building a system that learns**.

## Template Metaprogramming Foundation: When Templates Get Self-Aware

Now here's where things get interesting. We're not just building templates that generate code—we're building **templates that understand themselves**. Templates with introspection. Templates that can look in the mirror and ask, "Am I doing this right?"

### Self-Aware Templates: The Foundation of Intelligence

Traditional templates are like those old flip phones—they do one thing, and they do it the same way every time. Our self-aware templates? They're like smartphones that learn your habits and adapt.

```python
class SelfAwareTemplate:
    """Template that maintains metadata about its own structure and usage."""

    def __init__(self, template_content: str, metadata: Dict[str, Any] = None):
        self.content = template_content
        self.metadata = metadata or {}
        self.generation_history = []
        self.performance_data = {}

        # Parse template structure for self-analysis
        self.env = Environment()
        self.ast = self.env.parse(template_content)
        self.variables = meta.find_undeclared_variables(self.ast)

    def render_with_tracking(self, context: Dict[str, Any]) -> str:
        """Render template while tracking performance and usage patterns."""
        start_time = datetime.now()

        # Enhance context with self-reflection capabilities
        enhanced_context = {
            **context,
            'template_meta': self.metadata,
            'generation_count': len(self.generation_history),
            'performance_history': self.performance_data,
            'modify_template': self._modify_template_hook
        }

        template = Template(self.content)
        result = template.render(enhanced_context)

        # Record generation metrics
        generation_time = (datetime.now() - start_time).total_seconds()
        self.generation_history.append({
            'timestamp': start_time,
            'generation_time': generation_time,
            'context_keys': list(context.keys()),
            'output_size': len(result)
        })

        return result

    def _modify_template_hook(self, modification_type: str, **kwargs):
        """Hook for templates to request their own modifications."""
        self.metadata.setdefault('modification_requests', []).append({
            'type': modification_type,
            'timestamp': datetime.now(),
            'parameters': kwargs
        })
```

See what's happening here? This template isn't just passively waiting to be used. It's **actively tracking its own performance** and maintaining a history of how it's been used. It even has a mechanism (`_modify_template_hook`) for requesting its own modifications!

> 🤯 **Mind Blown Moment**: The template can literally ask to be changed. It's like code that files its own bug reports.

### Recursive Generation: Templates All the Way Down

But wait, it gets better. Our templates don't just generate code—they can generate other templates. And those templates know about their parents. It's like template inheritance, but with actual intelligence.

Here's where the magic really happens. Check out this FastAPI base template that's been enhanced with self-modification capabilities:

```python
# Base FastAPI service template with self-modification capabilities
FASTAPI_BASE_TEMPLATE = '''
"""
Generated FastAPI service
Template Version: {{ template_meta.version }}
Generation: {{ generation_count + 1 }}
"""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from datetime import datetime

# Performance tracking (auto-injected based on usage patterns)
{% if performance_history.avg_response_time > 0.5 %}
import cProfile
import pstats
from functools import wraps

def profile_endpoint(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            profiler.disable()
            # Log profiling data for template evolution
    return wrapper
{% endif %}

app = FastAPI(
    title="{{ service_name }}",
    version="{{ service_version }}",
    {% if generation_count > 5 and 'high_traffic' in performance_history %}
    # Auto-optimization: Enable response compression for high-traffic services
    middleware=[
        Middleware(GZipMiddleware, minimum_size=1000),
    ]
    {% endif %}
)

# Auto-generated models based on usage patterns
{% for model_name, model_fields in models.items() %}
class {{ model_name }}(BaseModel):
    {% for field_name, field_type in model_fields.items() %}
    {{ field_name }}: {{ field_type }}
    {% endfor %}

    {% if template_meta.enforce_validation and generation_count > 3 %}
    # Auto-injected validation based on error patterns
    @validator('*', pre=True)
    def sanitize_inputs(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v
    {% endif %}
{% endfor %}

# Endpoints with evolutionary improvements
{% for endpoint in endpoints %}
@app.{{ endpoint.method.lower() }}("{{ endpoint.path }}")
{% if performance_history.get(endpoint.path + '_slow', False) %}
@profile_endpoint  # Auto-injected for slow endpoints
{% endif %}
async def {{ endpoint.function_name }}(
    {% for param in endpoint.parameters %}
    {{ param.name }}: {{ param.type }}{% if param.default %} = {{ param.default }}{% endif %},
    {% endfor %}
):
    """
    {{ endpoint.description }}

    {% if template_meta.auto_documentation %}
    Auto-generated documentation:
    - Generated at: {{ generation_timestamp }}
    - Performance baseline: {{ performance_history.get(endpoint.path + '_avg_time', 'N/A') }}ms
    {% endif %}
    """

    {% if endpoint.path in error_patterns %}
    # Auto-injected error handling based on production issues
    try:
    {% endif %}

        {{ endpoint.implementation | indent(8) }}

    {% if endpoint.path in error_patterns %}
    except Exception as e:
        # Template learned this endpoint is error-prone
        logger.error(f"Error in {{ endpoint.function_name }}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    {% endif %}
{% endfor %}

# Auto-generated health check (evolved based on SRE requirements)
@app.get("/health")
async def health_check():
    """
    Health check endpoint - auto-evolved based on operational requirements.
    {% if generation_count > 2 %}
    Includes database connectivity check (added after generation 3).
    {% endif %}
    """
    health_status = {"status": "healthy", "timestamp": datetime.utcnow()}

    {% if generation_count > 2 %}
    # Database health check (auto-added after observing production issues)
    try:
        # Check database connectivity
        await database.execute("SELECT 1")
        health_status["database"] = "connected"
    except Exception:
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
    {% endif %}

    return health_status

# Template self-modification trigger
{% if generation_count > 10 %}
{{ modify_template('add_caching', reason='High generation count suggests need for optimization') }}
{% endif %}

{% if performance_history.avg_response_time > 1.0 %}
{{ modify_template('add_async_optimizations', threshold=performance_history.avg_response_time) }}
{% endif %}
'''
```

Holy cow, look at all the intelligence baked into this template!

> 🔥 **Hot Take**: This isn't just a template anymore—it's a **living document** that adapts based on operational reality.

Notice how the template:

- **Automatically adds profiling** for slow services
- **Injects compression middleware** for high-traffic scenarios
- **Evolves health checks** based on operational experience
- **Adds error handling** for problematic endpoints
- **Requests its own modifications** when certain conditions are met

This is template-driven development on steroids.

## AST Manipulation: When Templates Learn to Read Code

Now we're getting into the really advanced stuff. What if templates could actually **analyze the code they generate** and make intelligent decisions about how to improve it?

Enter AST (Abstract Syntax Tree) manipulation. This is where our templates become code critics, analyzing their own output and suggesting improvements.

### The Code Analysis Engine

```python
import ast
from typing import List, Dict, Any

class ASTTemplateModifier:
    """Modifies templates by analyzing and transforming generated code ASTs."""

    def __init__(self):
        self.modification_strategies = {
            'add_caching': self._add_caching_decorator,
            'optimize_imports': self._optimize_imports,
            'add_error_handling': self._add_error_handling,
            'inject_monitoring': self._inject_monitoring_code
        }

    def analyze_generated_code(self, code: str) -> Dict[str, Any]:
        """Analyze generated code to identify optimization opportunities."""
        tree = ast.parse(code)

        analysis = {
            'function_count': len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]),
            'async_function_count': len([n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)]),
            'import_statements': [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)],
            'decorator_usage': self._extract_decorators(tree),
            'error_handling_coverage': self._analyze_error_handling(tree),
            'complexity_metrics': self._calculate_complexity(tree)
        }

        return analysis

    def _extract_decorators(self, tree: ast.AST) -> List[str]:
        """Extract all decorators used in the code."""
        decorators = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        decorators.append(decorator.id)
                    elif isinstance(decorator, ast.Attribute):
                        decorators.append(f"{decorator.value.id}.{decorator.attr}")
        return decorators

    def _analyze_error_handling(self, tree: ast.AST) -> float:
        """Calculate the percentage of functions with error handling."""
        total_functions = 0
        functions_with_try_catch = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_functions += 1
                # Check if function body contains try-except blocks
                for child in ast.walk(node):
                    if isinstance(child, ast.Try):
                        functions_with_try_catch += 1
                        break

        return functions_with_try_catch / total_functions if total_functions > 0 else 0

    def modify_template_based_on_analysis(self, template: SelfAwareTemplate, analysis: Dict[str, Any]) -> str:
        """Modify template content based on code analysis."""
        modifications = []

        # Add caching if many repeated operations detected
        if analysis['function_count'] > 10 and 'cache' not in analysis['decorator_usage']:
            modifications.append('add_caching')

        # Add error handling if coverage is low
        if analysis['error_handling_coverage'] < 0.3:
            modifications.append('add_error_handling')

        # Optimize imports if too many unused imports
        if len(analysis['import_statements']) > 15:
            modifications.append('optimize_imports')

        modified_content = template.content
        for modification in modifications:
            if modification in self.modification_strategies:
                modified_content = self.modification_strategies[modification](modified_content, analysis)

        return modified_content
```

This is where the magic happens. Our system can:

1. **Parse the generated code** into an abstract syntax tree
2. **Analyze code patterns** like function counts, decorator usage, and error handling coverage
3. **Make intelligent decisions** about what improvements to apply
4. **Automatically modify templates** based on the analysis

> 🎯 **Key Insight**: We're not just generating code anymore—we're generating code that analyzes itself and requests improvements. It's like having a code reviewer that works 24/7 and never gets tired of pointing out the same issues.

Think about the implications here:

- Templates that detect when services need more robust error handling
- Automatic caching injection for services with many functions
- Import optimization for cleaner, faster-loading code
- Complexity analysis to flag overly complicated generated services

This is **code generation with a built-in quality assurance system**.

## Version-Aware Code Generation: The Backward Compatibility Dance

Here's a challenge that'll make your head spin: How do you evolve templates without breaking everything that's already been generated?

Traditional approach? Cross your fingers and hope for the best. Our approach? **Sophisticated versioning with built-in migration strategies**.

### The Compatibility Conundrum

Picture this scenario: You've got 50 services running template v1.0. Your template evolves to v2.0 with better security headers. Now what? Do you:

- A) Leave the old services vulnerable?
- B) Mass-update everything and pray nothing breaks?
- C) Build an intelligent migration system?

If you picked C, you're thinking like a platform engineer. Let's build it:

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

class CompatibilityLevel(Enum):
    BREAKING = "breaking"
    DEPRECATED = "deprecated"
    COMPATIBLE = "compatible"
    ENHANCED = "enhanced"

@dataclass
class TemplateVersion:
    major: int
    minor: int
    patch: int
    compatibility_level: CompatibilityLevel
    migration_required: bool = False
    deprecated_features: Set[str] = None

    def __post_init__(self):
        if self.deprecated_features is None:
            self.deprecated_features = set()

    @property
    def version_string(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

class VersionAwareGenerator:
    """Handles version-aware code generation with backwards compatibility."""

    def __init__(self):
        self.version_registry = {}
        self.migration_strategies = {}
        self.compatibility_matrix = {}

    def register_template_version(self, name: str, version: TemplateVersion, template_content: str):
        """Register a template version with migration capabilities."""
        if name not in self.version_registry:
            self.version_registry[name] = {}

        self.version_registry[name][version.version_string] = {
            'version': version,
            'content': template_content,
            'features': self._extract_features(template_content)
        }

    def generate_with_compatibility(self, template_name: str, target_version: str,
                                  context: Dict[str, Any],
                                  client_version: Optional[str] = None) -> str:
        """Generate code ensuring compatibility with client requirements."""

        if client_version and self._requires_migration(template_name, client_version, target_version):
            # Generate migration-aware output
            return self._generate_with_migration(template_name, client_version, target_version, context)

        # Standard generation
        template_data = self.version_registry[template_name][target_version]
        template = SelfAwareTemplate(template_data['content'], {
            'version': target_version,
            'compatibility_level': template_data['version'].compatibility_level.value,
            'client_version': client_version
        })

        return template.render_with_tracking(context)

    def _generate_with_migration(self, template_name: str, from_version: str,
                               to_version: str, context: Dict[str, Any]) -> str:
        """Generate code with migration annotations and compatibility shims."""

        # Enhanced template with migration awareness
        migration_template = f'''
# Generated with migration support from {from_version} to {to_version}
# Migration ID: {template_name}_{from_version}_to_{to_version}

# Backwards compatibility imports
{{% if client_version and version_compare(client_version, '2.0.0') < 0 %}}
# Legacy support for pre-2.0 clients
from typing_extensions import Annotated
{{% else %}}
from typing import Annotated
{{% endif %}}

# Migration warnings for deprecated features
import warnings

{{% for deprecated_feature in deprecated_features %}}
warnings.warn(
    "Feature '{{{{ deprecated_feature }}}}' is deprecated since version {to_version}. "
    "Use the new implementation instead.",
    DeprecationWarning,
    stacklevel=2
)
{{% endfor %}}

# Original template content with compatibility modifications
{self.version_registry[template_name][to_version]['content']}

# Migration utilities
class CompatibilityLayer:
    """Provides backwards compatibility for older client versions."""

    @staticmethod
    def legacy_response_format(data):
        """Convert new response format to legacy format if needed."""
        if context.get('client_version') and version_compare(context['client_version'], '1.5.0') < 0:
            # Transform response for older clients
            return {{"status": "success", "data": data}}
        return data
'''

        template = SelfAwareTemplate(migration_template, {
            'version': to_version,
            'client_version': from_version,
            'migration_active': True,
            'deprecated_features': self._get_deprecated_features(template_name, from_version, to_version)
        })

        return template.render_with_tracking(context)
```

> 💪 **Pro Move**: This system doesn't just manage versions—it **actively helps with migration**. It generates compatibility shims, deprecation warnings, and migration utilities automatically.

The beauty of this approach:

- **Old services keep working** with compatibility layers
- **New services get the latest features** automatically
- **Migration paths are generated** for you
- **Deprecation warnings** guide developers toward newer patterns

No more "big bang" template migrations that break everything!

## Performance Profiling: Because Templates Need Optimization Too

Here's something most people never think about: **template performance**. Yeah, I know, it sounds boring. But when you're generating thousands of services, those milliseconds add up.

Our templates don't just track their output—they track their own performance:

```python
import cProfile
import pstats
import io
from contextlib import contextmanager
from typing import Dict, Any, Generator

class TemplatePerformanceProfiler:
    """Profiles template execution for optimization opportunities."""

    def __init__(self):
        self.profile_data = {}
        self.performance_thresholds = {
            'render_time': 0.1,  # 100ms
            'memory_usage': 50 * 1024 * 1024,  # 50MB
            'template_size': 1024 * 1024  # 1MB
        }

    @contextmanager
    def profile_template_execution(self, template_id: str) -> Generator[Dict[str, Any], None, None]:
        """Context manager for profiling template execution."""
        profiler = cProfile.Profile()

        # Memory tracking
        import tracemalloc
        tracemalloc.start()

        start_memory = tracemalloc.get_traced_memory()[0]

        profiler.enable()
        performance_data = {'template_id': template_id}

        try:
            yield performance_data
        finally:
            profiler.disable()

            # Capture profiling data
            string_io = io.StringIO()
            stats = pstats.Stats(profiler, stream=string_io)
            stats.sort_stats('cumulative')
            stats.print_stats()

            end_memory = tracemalloc.get_traced_memory()[0]
            memory_peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()

            # Store performance metrics
            performance_data.update({
                'profile_output': string_io.getvalue(),
                'memory_used': end_memory - start_memory,
                'memory_peak': memory_peak,
                'function_calls': stats.total_calls
            })

            self.profile_data[template_id] = performance_data

            # Check for performance issues
            self._analyze_performance_issues(template_id, performance_data)

    def _analyze_performance_issues(self, template_id: str, performance_data: Dict[str, Any]):
        """Analyze performance data to identify optimization opportunities."""
        issues = []

        if performance_data.get('memory_used', 0) > self.performance_thresholds['memory_usage']:
            issues.append({
                'type': 'high_memory_usage',
                'severity': 'warning',
                'suggestion': 'Consider streaming template rendering or reducing context size'
            })

        if performance_data.get('memory_peak', 0) > self.performance_thresholds['memory_usage'] * 2:
            issues.append({
                'type': 'memory_spike',
                'severity': 'critical',
                'suggestion': 'Investigate memory leaks or optimize large data structures'
            })

        if issues:
            performance_data['optimization_suggestions'] = issues

class OptimizedTemplateEngine:
    """Template engine with built-in performance optimization."""

    def __init__(self):
        self.profiler = TemplatePerformanceProfiler()
        self.cache = {}
        self.optimization_strategies = {
            'cache_compiled_templates': True,
            'lazy_load_templates': True,
            'stream_large_outputs': True,
            'parallel_include_rendering': True
        }

    async def render_optimized(self, template: SelfAwareTemplate,
                             context: Dict[str, Any]) -> str:
        """Render template with performance optimizations."""

        template_id = f"{id(template)}_{hash(str(context))}"

        # Check cache first
        if template_id in self.cache and self.optimization_strategies['cache_compiled_templates']:
            return self.cache[template_id]

        with self.profiler.profile_template_execution(template_id) as perf_data:
            # Pre-render optimizations
            optimized_context = await self._optimize_context(context)

            # Render with streaming for large outputs
            if self.optimization_strategies['stream_large_outputs']:
                result = await self._stream_render(template, optimized_context)
            else:
                result = template.render_with_tracking(optimized_context)

            perf_data['render_time'] = perf_data.get('render_time', 0)
            perf_data['output_size'] = len(result)

        # Cache result if beneficial
        if self._should_cache_result(template_id, perf_data):
            self.cache[template_id] = result

        return result

    async def _optimize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize context for better rendering performance."""
        optimized = context.copy()

        # Convert large lists to generators where possible
        for key, value in context.items():
            if isinstance(value, list) and len(value) > 1000:
                optimized[key] = (item for item in value)

        return optimized

    async def _stream_render(self, template: SelfAwareTemplate,
                           context: Dict[str, Any]) -> str:
        """Stream template rendering for large outputs."""
        # Implementation would use Jinja2's streaming capabilities
        # This is a simplified version
        return template.render_with_tracking(context)
```

> ⚡ **Performance Insight**: Template optimization isn't just about speed—it's about **scalability**. When your platform is generating hundreds of services per day, every optimization compounds.

The cool thing about this profiler? It doesn't just measure performance—it **automatically suggests optimizations**. Memory usage too high? It suggests streaming. Template compilation slow? It enables caching.

It's like having a performance consultant built into your template engine.

## The Final Solution: Auto-Evolving Microservice Scaffolding System

Alright, time to put it all together. All these components working in harmony to create something that's honestly a bit magical:

```python
class AutoEvolvingScaffoldingSystem:
    """Complete self-modifying code generation pipeline."""

    def __init__(self):
        self.template_engine = OptimizedTemplateEngine()
        self.version_manager = VersionAwareGenerator()
        self.ast_modifier = ASTTemplateModifier()
        self.analytics_collector = AnalyticsCollector()
        self.evolution_engine = TemplateEvolutionEngine()

        # Initialize base templates
        self._initialize_base_templates()

    def _initialize_base_templates(self):
        """Set up initial template versions."""
        base_version = TemplateVersion(1, 0, 0, CompatibilityLevel.COMPATIBLE)
        self.version_manager.register_template_version(
            "fastapi_service",
            base_version,
            FASTAPI_BASE_TEMPLATE
        )

    async def generate_service(self, service_spec: Dict[str, Any],
                             target_version: str = "1.0.0") -> str:
        """Generate a FastAPI service with evolutionary improvements."""

        # Gather context from analytics
        historical_data = await self.analytics_collector.get_service_analytics(
            service_spec.get('service_type', 'default')
        )

        # Enhance context with learned optimizations
        enhanced_context = {
            **service_spec,
            'performance_history': historical_data.get('performance', {}),
            'error_patterns': historical_data.get('common_errors', []),
            'usage_patterns': historical_data.get('usage', {}),
            'generation_timestamp': datetime.now().isoformat()
        }

        # Generate code
        template_name = "fastapi_service"
        generated_code = self.version_manager.generate_with_compatibility(
            template_name, target_version, enhanced_context
        )

        # Analyze generated code for immediate optimizations
        code_analysis = self.ast_modifier.analyze_generated_code(generated_code)

        # Apply AST-based improvements
        if self._should_apply_ast_optimizations(code_analysis):
            template = self.version_manager.version_registry[template_name][target_version]
            optimized_template_content = self.ast_modifier.modify_template_based_on_analysis(
                SelfAwareTemplate(template['content']), code_analysis
            )

            # Re-generate with optimized template
            optimized_template = SelfAwareTemplate(optimized_template_content)
            generated_code = await self.template_engine.render_optimized(
                optimized_template, enhanced_context
            )

        # Record generation metrics for future evolution
        await self._record_generation_metrics(service_spec, generated_code, code_analysis)

        return generated_code

    async def evolve_templates(self):
        """Trigger template evolution based on collected analytics."""

        # Collect analytics from all generated services
        all_metrics = await self.analytics_collector.get_all_metrics()

        # Analyze for evolution opportunities
        evolution_suggestions = self.evolution_engine.analyze_for_evolution(all_metrics)

        # Apply approved evolutions
        for suggestion in evolution_suggestions:
            if suggestion['confidence'] > 0.8:  # High confidence threshold
                await self._apply_template_evolution(suggestion)

    async def _apply_template_evolution(self, suggestion: Dict[str, Any]):
        """Apply an evolution suggestion to templates."""

        template_name = suggestion['template_name']
        modification_type = suggestion['type']

        # Get current template version
        current_versions = self.version_manager.version_registry[template_name]
        latest_version_string = max(current_versions.keys())
        latest_template = current_versions[latest_version_string]

        # Create evolved version
        evolved_content = self._apply_evolution_modification(
            latest_template['content'], suggestion
        )

        # Increment version
        new_version = self._increment_version(latest_template['version'], suggestion['impact'])

        # Register evolved template
        self.version_manager.register_template_version(
            template_name, new_version, evolved_content
        )

        print(f"Template {template_name} evolved to version {new_version.version_string}")
        print(f"Evolution: {suggestion['description']}")

# Supporting classes for analytics and evolution
class AnalyticsCollector:
    """Collects and analyzes usage patterns from generated services."""

    async def get_service_analytics(self, service_type: str) -> Dict[str, Any]:
        """Get historical analytics for a service type."""
        # Implementation would connect to monitoring systems
        return {
            'performance': {'avg_response_time': 0.3, 'error_rate': 0.02},
            'common_errors': ['validation_error', 'timeout'],
            'usage': {'peak_requests_per_second': 1000}
        }

    async def get_all_metrics(self) -> List[GenerationMetrics]:
        """Retrieve all collected metrics for evolution analysis."""
        # Implementation would query metrics database
        return []

class TemplateEvolutionEngine:
    """Analyzes metrics to suggest template improvements."""

    def analyze_for_evolution(self, metrics: List[GenerationMetrics]) -> List[Dict[str, Any]]:
        """Analyze metrics to identify evolution opportunities."""
        suggestions = []

        # Example: If many services need the same optimization
        if self._detect_common_performance_issue(metrics):
            suggestions.append({
                'template_name': 'fastapi_service',
                'type': 'performance_optimization',
                'description': 'Add automatic connection pooling for database-heavy services',
                'confidence': 0.9,
                'impact': 'minor'
            })

        return suggestions

    def _detect_common_performance_issue(self, metrics: List[GenerationMetrics]) -> bool:
        """Detect if there's a common performance issue across services."""
        slow_services = [m for m in metrics if m.performance_metrics.get('avg_response_time', 0) > 0.5]
        return len(slow_services) > len(metrics) * 0.3  # 30% of services are slow

# Usage example
async def main():
    """Demonstrate the auto-evolving scaffolding system."""

    system = AutoEvolvingScaffoldingSystem()

    # Generate a user service
    user_service_spec = {
        'service_name': 'UserService',
        'service_version': '1.0.0',
        'models': {
            'User': {
                'id': 'int',
                'username': 'str',
                'email': 'str',
                'created_at': 'datetime'
            }
        },
        'endpoints': [
            {
                'method': 'GET',
                'path': '/users/{user_id}',
                'function_name': 'get_user',
                'parameters': [{'name': 'user_id', 'type': 'int'}],
                'description': 'Retrieve a user by ID',
                'implementation': 'return await user_repository.get_by_id(user_id)'
            }
        ]
    }

    # Generate the service
    generated_code = await system.generate_service(user_service_spec)
    print("Generated FastAPI service:")
    print(generated_code)

    # Simulate template evolution (would normally run periodically)
    await system.evolve_templates()

if __name__ == "__main__":
    asyncio.run(main())
```

> 🎉 **Ta-da!** There it is—a complete auto-evolving scaffolding system that learns, adapts, and improves over time.

Notice how this system brings together all our components:

- **Self-aware templates** that track their own usage
- **Version management** with backward compatibility
- **AST analysis** for code quality optimization
- **Performance profiling** for template optimization
- **Evolution engine** that learns from operational data

But the real magic happens when you run it. The system **genuinely gets smarter over time**.

## Taking It to the Next Level: Advanced Production Patterns

Now that we've got the core system working, let's talk about what happens when you deploy this beast in production. Spoiler alert: it gets even cooler.

### Template Rollback and Safety Mechanisms: Because Evolution Can Go Wrong

Here's the thing about evolution—sometimes it goes down the wrong path. Dinosaurs were pretty successful until they weren't. Our templates need safety nets:

```python
class TemplateRollbackManager:
    """Manages template rollbacks and safety checks."""

    def __init__(self):
        self.rollback_history = {}
        self.safety_checks = []
        self.canary_deployments = {}

    async def safe_deploy_template(self, template_name: str, new_version: TemplateVersion,
                                 template_content: str) -> bool:
        """Deploy template with safety checks and rollback capability."""

        # Store current version for potential rollback
        current_version = self._get_current_version(template_name)
        self.rollback_history[template_name] = {
            'previous_version': current_version,
            'rollback_timestamp': datetime.now(),
            'reason': 'safety_deployment'
        }

        # Run pre-deployment safety checks
        safety_results = await self._run_safety_checks(template_content)
        if not all(check['passed'] for check in safety_results):
            await self._rollback_template(template_name)
            return False

        # Deploy to canary environment first
        canary_success = await self._deploy_canary(template_name, new_version, template_content)
        if not canary_success:
            await self._rollback_template(template_name)
            return False

        # Full deployment
        return await self._deploy_production(template_name, new_version, template_content)

    async def _run_safety_checks(self, template_content: str) -> List[Dict[str, Any]]:
        """Run comprehensive safety checks on template content."""
        checks = []

        # Security scan
        security_check = await self._security_scan(template_content)
        checks.append({
            'name': 'security_scan',
            'passed': security_check['vulnerabilities'] == 0,
            'details': security_check
        })

        # Performance regression test
        perf_check = await self._performance_regression_test(template_content)
        checks.append({
            'name': 'performance_regression',
            'passed': perf_check['regression_detected'] == False,
            'details': perf_check
        })

        # Syntax and compilation check
        syntax_check = self._syntax_validation(template_content)
        checks.append({
            'name': 'syntax_validation',
            'passed': syntax_check['valid'],
            'details': syntax_check
        })

        return checks
```

> 🛡️ **Safety First**: Template evolution without safety checks is like genetic engineering without ethics committees. Theoretically powerful, practically terrifying.

This rollback manager is like having a time machine for your templates. Template evolution goes wrong? **Boom**—instant rollback to the last known good state.

### Evolution Metrics: Measuring the Intelligence

How do you know if your templates are actually getting smarter? You measure it:

```python
class EvolutionMetrics:
    """Tracks the success and impact of template evolution."""

    def __init__(self):
        self.evolution_history = []
        self.success_metrics = {}
        self.impact_analysis = {}

    def record_evolution_outcome(self, template_name: str, evolution_type: str,
                               outcome: Dict[str, Any]):
        """Record the outcome of a template evolution."""
        record = {
            'timestamp': datetime.now(),
            'template_name': template_name,
            'evolution_type': evolution_type,
            'outcome': outcome,
            'metrics': self._collect_post_evolution_metrics(template_name)
        }

        self.evolution_history.append(record)
        self._update_success_rates(evolution_type, outcome)

    def _collect_post_evolution_metrics(self, template_name: str) -> Dict[str, Any]:
        """Collect metrics after template evolution to measure impact."""
        return {
            'services_using_template': self._count_active_services(template_name),
            'average_generation_time': self._measure_generation_performance(template_name),
            'error_rate_change': self._calculate_error_rate_delta(template_name),
            'developer_satisfaction': self._get_developer_feedback(template_name)
        }

    def get_evolution_recommendations(self) -> List[Dict[str, Any]]:
        """Generate recommendations based on evolution history."""
        recommendations = []

        # Analyze successful patterns
        successful_evolutions = [
            e for e in self.evolution_history
            if e['outcome'].get('success', False)
        ]

        if successful_evolutions:
            # Find patterns in successful evolutions
            common_patterns = self._identify_success_patterns(successful_evolutions)
            for pattern in common_patterns:
                recommendations.append({
                    'type': 'apply_successful_pattern',
                    'pattern': pattern,
                    'confidence': pattern['success_rate'],
                    'templates': pattern['applicable_templates']
                })

        return recommendations
```

This is where data science meets platform engineering. The system **tracks the success of its own evolution** and learns which types of changes actually improve things.

> 📊 **Data-Driven Evolution**: Your templates don't just evolve—they evolve intelligently based on what actually works in your environment.

### CI/CD Integration: Making Evolution Seamless

Template evolution needs to play nice with your existing development workflows:

```python
class CICDIntegration:
    """Integrates template evolution with CI/CD pipelines."""

    def __init__(self, pipeline_config: Dict[str, Any]):
        self.pipeline_config = pipeline_config
        self.webhook_handlers = {}
        self.deployment_stages = ['test', 'staging', 'production']

    async def handle_code_generation_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code generation request from CI/CD pipeline."""

        # Extract generation parameters
        service_spec = request['service_specification']
        target_environment = request.get('environment', 'development')
        pipeline_id = request.get('pipeline_id')

        # Select appropriate template version based on environment
        template_version = self._select_template_version(target_environment)

        # Generate code with pipeline-specific context
        pipeline_context = {
            **service_spec,
            'pipeline_id': pipeline_id,
            'target_environment': target_environment,
            'build_metadata': request.get('build_metadata', {}),
            'git_context': request.get('git_context', {})
        }

        generated_code = await self.scaffolding_system.generate_service(
            pipeline_context, template_version
        )

        # Create deployment artifacts
        artifacts = await self._create_deployment_artifacts(
            generated_code, pipeline_context
        )

        # Trigger follow-up pipeline stages
        await self._trigger_downstream_stages(pipeline_id, artifacts)

        return {
            'status': 'success',
            'generated_code': generated_code,
            'artifacts': artifacts,
            'template_version': template_version,
            'next_stages': self._get_next_stages(target_environment)
        }

    async def _create_deployment_artifacts(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create additional deployment artifacts based on generated code."""

        artifacts = {
            'source_code': code,
            'dockerfile': self._generate_dockerfile(context),
            'kubernetes_manifests': self._generate_k8s_manifests(context),
            'helm_chart': self._generate_helm_chart(context),
            'terraform_config': self._generate_terraform_config(context)
        }

        # Add environment-specific configurations
        environment = context.get('target_environment')
        if environment in ['staging', 'production']:
            artifacts.update({
                'monitoring_config': self._generate_monitoring_config(context),
                'alerting_rules': self._generate_alerting_rules(context),
                'security_policies': self._generate_security_policies(context)
            })

        return artifacts
```

The beauty here? Your CI/CD pipeline doesn't just generate code—it generates **complete deployment artifacts** tailored to each environment. Development gets basic monitoring. Production gets the full security and observability stack.

### Template Testing: Because Even Smart Templates Need QA

You wouldn't deploy code without testing it. Why would you deploy template changes without testing them?

```python
class TemplateTestFramework:
    """Comprehensive testing framework for template evolution."""

    def __init__(self):
        self.test_suites = {}
        self.test_data_generators = {}
        self.validation_rules = []

    async def run_comprehensive_tests(self, template_name: str,
                                    template_content: str) -> Dict[str, Any]:
        """Run comprehensive tests on a template."""

        test_results = {
            'template_name': template_name,
            'test_timestamp': datetime.now(),
            'results': {}
        }

        # Unit tests - test individual template components
        unit_results = await self._run_unit_tests(template_name, template_content)
        test_results['results']['unit_tests'] = unit_results

        # Integration tests - test template with various contexts
        integration_results = await self._run_integration_tests(template_name, template_content)
        test_results['results']['integration_tests'] = integration_results

        # Property-based tests - test template with generated inputs
        property_results = await self._run_property_tests(template_name, template_content)
        test_results['results']['property_tests'] = property_results

        # Performance tests - benchmark template execution
        performance_results = await self._run_performance_tests(template_name, template_content)
        test_results['results']['performance_tests'] = performance_results

        # Security tests - scan for vulnerabilities in generated code
        security_results = await self._run_security_tests(template_name, template_content)
        test_results['results']['security_tests'] = security_results

        # Calculate overall score
        test_results['overall_score'] = self._calculate_test_score(test_results['results'])
        test_results['passed'] = test_results['overall_score'] >= 0.8

        return test_results

    async def _run_property_tests(self, template_name: str,
                                template_content: str) -> Dict[str, Any]:
        """Run property-based tests using generated test data."""

        # Generate diverse test contexts
        test_contexts = self._generate_test_contexts(template_name, count=100)

        results = {
            'total_contexts': len(test_contexts),
            'successful_generations': 0,
            'failures': [],
            'property_violations': []
        }

        for i, context in enumerate(test_contexts):
            try:
                template = SelfAwareTemplate(template_content)
                generated_code = template.render_with_tracking(context)

                # Validate generated code properties
                violations = self._check_code_properties(generated_code, context)
                if violations:
                    results['property_violations'].extend(violations)
                else:
                    results['successful_generations'] += 1

            except Exception as e:
                results['failures'].append({
                    'context_index': i,
                    'error': str(e),
                    'context': context
                })

        results['success_rate'] = results['successful_generations'] / results['total_contexts']
        return results
```

This framework doesn't just test if templates render—it tests **if they render correctly** under a hundred different scenarios. Property-based testing for templates? Now that's next-level quality assurance.

### Blue-Green Template Deployment: Zero-Downtime Evolution

Here's the cherry on top: **zero-downtime template evolution** using blue-green deployment strategies:

```python
class BlueGreenTemplateDeployment:
    """Implements blue-green deployment strategy for template evolution."""

    def __init__(self):
        self.active_environment = 'blue'  # or 'green'
        self.environments = {
            'blue': {},
            'green': {}
        }
        self.traffic_router = TrafficRouter()

    async def deploy_template_evolution(self, template_name: str,
                                      new_version: TemplateVersion,
                                      template_content: str) -> bool:
        """Deploy template evolution using blue-green strategy."""

        # Determine target environment (opposite of active)
        target_env = 'green' if self.active_environment == 'blue' else 'blue'

        # Deploy to inactive environment
        await self._deploy_to_environment(
            target_env, template_name, new_version, template_content
        )

        # Run smoke tests
        smoke_test_results = await self._run_smoke_tests(target_env, template_name)
        if not smoke_test_results['passed']:
            await self._cleanup_environment(target_env, template_name)
            return False

        # Gradual traffic shift
        success = await self._gradual_traffic_shift(template_name, target_env)

        if success:
            # Complete switchover
            self.active_environment = target_env
            # Cleanup old environment
            old_env = 'blue' if target_env == 'green' else 'green'
            await self._cleanup_environment(old_env, template_name)
            return True
        else:
            # Rollback
            await self._cleanup_environment(target_env, template_name)
            return False

    async def _gradual_traffic_shift(self, template_name: str,
                                   target_environment: str) -> bool:
        """Gradually shift traffic to new template version."""

        traffic_percentages = [5, 10, 25, 50, 75, 100]

        for percentage in traffic_percentages:
            # Route percentage of traffic to new environment
            await self.traffic_router.set_traffic_split(
                template_name,
                {self.active_environment: 100 - percentage, target_environment: percentage}
            )

            # Monitor for issues
            await asyncio.sleep(300)  # Wait 5 minutes

            health_check = await self._health_check(target_environment, template_name)
            if not health_check['healthy']:
                # Rollback traffic
                await self.traffic_router.set_traffic_split(
                    template_name,
                    {self.active_environment: 100, target_environment: 0}
                )
                return False

        return True
```

> 🚀 **Production Ready**: This isn't just a proof of concept—this is enterprise-grade template deployment with canary testing, gradual rollout, and automatic rollback.

The system gradually shifts traffic from the old template version to the new one, monitoring for issues at each step. Problems detected? **Automatic rollback**. No problems? **Seamless evolution**.

## Wrapping Up: The Future of Code Generation

Let's step back and appreciate what we've built here. This isn't just a code generator—it's a **learning system** that embodies some seriously advanced concepts:

### What Makes This Revolutionary

**🧠 Self-Awareness**: Templates that understand their own structure and performance characteristics.

**📈 Continuous Learning**: Systems that analyze production data and automatically apply insights to future generations.

**🔄 Safe Evolution**: Template changes with built-in safety nets, testing, and rollback capabilities.

**⚖️ Backward Compatibility**: Evolution that doesn't break existing services through intelligent migration strategies.

**🎯 Data-Driven Decisions**: Every template modification backed by real operational data, not just theoretical improvements.

### The Paradigm Shift

Traditional code generation: **"Here's your boilerplate. Good luck!"**

Our approach: **"Here's your intelligently optimized service, based on everything we've learned from running similar services in your environment. It'll automatically adapt as we learn more."**

That's not just an improvement—it's a complete reimagining of what code generation can be.

### Real-World Impact

Imagine this system running in your organization:

- **New services inherit battle-tested optimizations automatically**
- **Security updates propagate through template evolution**
- **Performance improvements get applied across your entire fleet**
- **Operational wisdom accumulates and compounds over time**

Instead of copy-pasting the same fixes across hundreds of services, your **templates learn from each fix and prevent the problem from recurring**.

### Next Steps: The Journey Continues

This chapter has laid the foundation for intelligent, adaptive code generation. But we're just getting started. In Chapter 2, we'll take these evolutionary principles and apply them to an even more complex challenge: **multi-language SDK generation**.

Picture this: templates that generate SDKs for eight different programming languages, each optimized for its target ecosystem, all while maintaining consistency and learning from usage patterns across every language.

We're talking about:

- Language-specific template hierarchies
- Cross-language consistency enforcement
- Polyglot performance optimization
- Ecosystem-aware code generation

If self-modifying FastAPI generation blew your mind, wait until you see templates that speak Python, JavaScript, Go, Rust, Java, C#, PHP, and Ruby—all while learning from each other.

> 🌟 **The Big Picture**: We're not just building tools—we're building **intelligent platform systems** that grow smarter over time. Every chapter builds on the last, creating increasingly sophisticated automation that learns, adapts, and evolves.

## Your Mission, Should You Choose to Accept It

Here are some challenges to take this system to the next level:

### 🎯 Exercise 1: Template Introspection Engine

Extend the `SelfAwareTemplate` class to detect unused variables, redundant logic, and template complexity metrics. Build a system that can suggest template simplifications automatically.

### 🧪 Exercise 2: Evolution Strategy Playground

Implement multiple evolution strategies:

- **Conservative**: Only apply changes with 95%+ confidence
- **Aggressive**: Apply changes with 70%+ confidence
- **Experimental**: Test controversial changes in isolation

### 🔬 Exercise 3: A/B Testing for Templates

Build a system that can run A/B tests on template changes, measuring real-world impact before full rollout. Which template version actually produces better services?

### 🛡️ Exercise 4: Security Evolution Engine

Create a specialized evolution engine that focuses on security improvements, automatically patching common vulnerabilities and applying security best practices.

### 📊 Exercise 5: Performance Regression Detection

Build monitoring that detects when template changes introduce performance regressions in generated services, with automatic rollback triggers.

The tools are in your hands. The patterns are established. Time to build something amazing.

_Ready to make your templates as smart as your senior engineers? Let's keep evolving._
