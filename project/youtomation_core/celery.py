"""
Celery Configuration
Production-ready async task queue setup
"""
import os
from celery import Celery
from celery.schedules import schedule
from celery.signals import task_prerun, task_postrun, task_failure

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youtomation_core.settings')

app = Celery('youtomation')

# Load configuration from Django settings with CELERY prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django app configs
app.autodiscover_tasks()

# ===== CELERY CONFIGURATION =====
app.conf.update(
    # Task routing
    task_routes={
        'youtomation_app.tasks.fetch_trending_topics': {'queue': 'high_priority'},
        'youtomation_app.tasks.generate_script': {'queue': 'default'},
        'youtomation_app.tasks.text_to_speech': {'queue': 'default'},
        'youtomation_app.tasks.fetch_stock_videos': {'queue': 'default'},
        'youtomation_app.tasks.generate_video': {'queue': 'high_priority'},
        'youtomation_app.tasks.upload_to_youtube': {'queue': 'high_priority'},
        'youtomation_app.tasks.generate_and_upload_youtube_video': {'queue': 'default'},
    },
    
    # Queue configuration
    task_queues=(
        ('default', {'exchange': 'default', 'routing_key': 'default', 'priority': 5}),
        ('high_priority', {'exchange': 'high_priority', 'routing_key': 'high_priority', 'priority': 10}),
    ),
    
    # Task execution settings
    task_acks_late=True,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    
    # Task retry settings
    task_default_retry_delay=60,  # 1 minute
    task_default_max_retries=3,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'retry_on_timeout': True,
        'socket_connect_timeout': 5,
        'socket_timeout': 5,
    },
)

# Additional Celery configurations
app.conf.worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
app.conf.worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'


# ===== CELERY SIGNALS =====
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **run_kwargs):
    """Handle pre-task run events"""
    import logging
    logger = logging.getLogger('celery')
    logger.info(f"Task {task.name} ({task_id}) started with args={args}, kwargs={kwargs}")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, **run_kwargs):
    """Handle post-task run events"""
    import logging
    logger = logging.getLogger('celery')
    logger.info(f"Task {task.name} ({task_id}) completed with result={retval}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, traceback=None, **kwargs):
    """Handle task failure events"""
    import logging
    logger = logging.getLogger('celery')
    logger.error(
        f"Task {sender.name} ({task_id}) failed: {exception}",
        exc_info=(type(exception), exception, traceback)
    )


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')
