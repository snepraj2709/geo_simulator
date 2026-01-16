# LLM Brand Influence Monitor - Deployment Guide

## Overview

This document covers the infrastructure architecture, deployment procedures, and operational guidelines for the LLM Brand Influence Monitor platform.

---

## Infrastructure Architecture

### Cloud Provider: AWS (Primary)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                    AWS Cloud                                     │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                           VPC (10.0.0.0/16)                              │    │
│  │                                                                          │    │
│  │  ┌──────────────────────────────────────────────────────────────────┐   │    │
│  │  │                    Public Subnets (10.0.1.0/24)                   │   │    │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │   │    │
│  │  │  │     ALB     │  │   NAT GW    │  │  Bastion    │               │   │    │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘               │   │    │
│  │  └──────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                          │    │
│  │  ┌──────────────────────────────────────────────────────────────────┐   │    │
│  │  │                   Private Subnets (10.0.2.0/24)                   │   │    │
│  │  │                                                                   │   │    │
│  │  │  ┌─────────────────────────────────────────────────────────┐     │   │    │
│  │  │  │                    EKS Cluster                          │     │   │    │
│  │  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │     │   │    │
│  │  │  │  │ API Svc │ │Scraper  │ │Simulator│ │Analytics│       │     │   │    │
│  │  │  │  │ (3 pods)│ │ (5 pods)│ │(10 pods)│ │ (3 pods)│       │     │   │    │
│  │  │  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │     │   │    │
│  │  │  │                                                         │     │   │    │
│  │  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐                   │     │   │    │
│  │  │  │  │ Celery  │ │ Celery  │ │ Celery  │                   │     │   │    │
│  │  │  │  │ Worker  │ │ Beat    │ │ Flower  │                   │     │   │    │
│  │  │  │  │(10 pods)│ │ (1 pod) │ │ (1 pod) │                   │     │   │    │
│  │  │  │  └─────────┘ └─────────┘ └─────────┘                   │     │   │    │
│  │  │  └─────────────────────────────────────────────────────────┘     │   │    │
│  │  │                                                                   │   │    │
│  │  └──────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                          │    │
│  │  ┌──────────────────────────────────────────────────────────────────┐   │    │
│  │  │                   Data Subnets (10.0.3.0/24)                      │   │    │
│  │  │                                                                   │   │    │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │   │    │
│  │  │  │    RDS      │  │ElastiCache  │  │  OpenSearch │               │   │    │
│  │  │  │ PostgreSQL  │  │   Redis     │  │   Cluster   │               │   │    │
│  │  │  │  (Multi-AZ) │  │  (Cluster)  │  │             │               │   │    │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘               │   │    │
│  │  │                                                                   │   │    │
│  │  └──────────────────────────────────────────────────────────────────┘   │    │
│  │                                                                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │       S3        │  │   CloudFront    │  │    Route 53     │                  │
│  │ (Object Store)  │  │     (CDN)       │  │     (DNS)       │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   CloudWatch    │  │    Secrets      │  │      KMS        │                  │
│  │   (Monitoring)  │  │    Manager      │  │  (Encryption)   │                  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                            External Services                                     │
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐                                       │
│  │   Neo4j Aura    │  │   LLM APIs      │                                       │
│  │ (Graph Database)│  │ (OpenAI, etc.)  │                                       │
│  └─────────────────┘  └─────────────────┘                                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Environment Configuration

### Environment Types

| Environment | Purpose | AWS Account |
|-------------|---------|-------------|
| `development` | Local development | N/A |
| `staging` | Pre-production testing | staging-account |
| `production` | Live system | production-account |

### Environment Variables

```bash
# Application
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<from-secrets-manager>

# Database
DATABASE_URL=postgresql://user:pass@host:5432/llm_brand_monitor
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Neo4j
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<from-secrets-manager>

# Redis
REDIS_URL=redis://elasticache-cluster.xxxxx.cache.amazonaws.com:6379
REDIS_POOL_SIZE=10

# Elasticsearch/OpenSearch
ELASTICSEARCH_URL=https://search-xxxxx.us-east-1.es.amazonaws.com
ELASTICSEARCH_USER=admin
ELASTICSEARCH_PASSWORD=<from-secrets-manager>

# S3
S3_BUCKET=llm-brand-monitor-production
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=<from-iam-role>
AWS_SECRET_ACCESS_KEY=<from-iam-role>

# LLM API Keys
OPENAI_API_KEY=<from-secrets-manager>
GOOGLE_API_KEY=<from-secrets-manager>
ANTHROPIC_API_KEY=<from-secrets-manager>
PERPLEXITY_API_KEY=<from-secrets-manager>

# Celery
CELERY_BROKER_URL=redis://elasticache-cluster.xxxxx.cache.amazonaws.com:6379/0
CELERY_RESULT_BACKEND=redis://elasticache-cluster.xxxxx.cache.amazonaws.com:6379/1

# Monitoring
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
DATADOG_API_KEY=<from-secrets-manager>

# Feature Flags
FEATURE_NEW_CLASSIFIER=true
FEATURE_PERPLEXITY_ENABLED=true
```

---

## Kubernetes Deployment

### Namespace Structure

```yaml
# namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: llm-brand-monitor
  labels:
    app: llm-brand-monitor
    environment: production
---
apiVersion: v1
kind: Namespace
metadata:
  name: llm-brand-monitor-jobs
  labels:
    app: llm-brand-monitor
    tier: background-jobs
```

### API Service Deployment

```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
  namespace: llm-brand-monitor
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-service
  template:
    metadata:
      labels:
        app: api-service
    spec:
      containers:
      - name: api
        image: llm-brand-monitor/api:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        envFrom:
        - secretRef:
            name: app-secrets
        - configMapRef:
            name: app-config
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: api-service
  namespace: llm-brand-monitor
spec:
  selector:
    app: api-service
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Scraper Service Deployment

```yaml
# scraper-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scraper-service
  namespace: llm-brand-monitor
spec:
  replicas: 5
  selector:
    matchLabels:
      app: scraper-service
  template:
    metadata:
      labels:
        app: scraper-service
    spec:
      containers:
      - name: scraper
        image: llm-brand-monitor/scraper:latest
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        envFrom:
        - secretRef:
            name: app-secrets
        - configMapRef:
            name: app-config
```

### Simulator Service Deployment

```yaml
# simulator-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: simulator-service
  namespace: llm-brand-monitor
spec:
  replicas: 10
  selector:
    matchLabels:
      app: simulator-service
  template:
    metadata:
      labels:
        app: simulator-service
    spec:
      containers:
      - name: simulator
        image: llm-brand-monitor/simulator:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        envFrom:
        - secretRef:
            name: app-secrets
        - configMapRef:
            name: app-config
```

### Celery Workers Deployment

```yaml
# celery-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: llm-brand-monitor-jobs
spec:
  replicas: 10
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: worker
        image: llm-brand-monitor/worker:latest
        command: ["celery", "-A", "app.celery", "worker", "-l", "info", "-Q", "default,scraping,simulation"]
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        envFrom:
        - secretRef:
            name: app-secrets
        - configMapRef:
            name: app-config
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-beat
  namespace: llm-brand-monitor-jobs
spec:
  replicas: 1
  selector:
    matchLabels:
      app: celery-beat
  template:
    metadata:
      labels:
        app: celery-beat
    spec:
      containers:
      - name: beat
        image: llm-brand-monitor/worker:latest
        command: ["celery", "-A", "app.celery", "beat", "-l", "info"]
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
```

### Horizontal Pod Autoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-service-hpa
  namespace: llm-brand-monitor
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-service
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker-hpa
  namespace: llm-brand-monitor-jobs
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-worker
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: External
    external:
      metric:
        name: celery_queue_length
      target:
        type: AverageValue
        averageValue: "10"
```

### Ingress Configuration

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: llm-brand-monitor
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:xxxxx:certificate/xxxxx
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/actions.ssl-redirect: '{"Type": "redirect", "RedirectConfig": {"Protocol": "HTTPS", "Port": "443", "StatusCode": "HTTP_301"}}'
spec:
  rules:
  - host: api.llmbrandmonitor.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
```

---

## Database Setup

### PostgreSQL (RDS)

```terraform
# terraform/rds.tf
resource "aws_db_instance" "main" {
  identifier     = "llm-brand-monitor-db"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.r6g.xlarge"

  allocated_storage     = 100
  max_allocated_storage = 500
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "llm_brand_monitor"
  username = "admin"
  password = var.db_password

  multi_az               = true
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"

  performance_insights_enabled = true

  tags = {
    Environment = "production"
    Application = "llm-brand-monitor"
  }
}
```

### Redis (ElastiCache)

```terraform
# terraform/elasticache.tf
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "llm-brand-monitor-redis"
  description                = "Redis cluster for LLM Brand Monitor"
  node_type                  = "cache.r6g.large"
  num_cache_clusters         = 3
  port                       = 6379

  engine               = "redis"
  engine_version       = "7.0"
  parameter_group_name = "default.redis7"

  automatic_failover_enabled = true
  multi_az_enabled          = true

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  snapshot_retention_limit = 7
  snapshot_window         = "05:00-06:00"

  tags = {
    Environment = "production"
    Application = "llm-brand-monitor"
  }
}
```

### Neo4j Aura (Managed)

Neo4j is deployed as a managed service via Neo4j Aura:

- **Instance Type:** Professional
- **Region:** US-East-1 (same as primary infrastructure)
- **Memory:** 8GB
- **Storage:** 16GB (auto-scaling)

Connection is via private endpoint with VPC peering configured.

### OpenSearch

```terraform
# terraform/opensearch.tf
resource "aws_opensearch_domain" "main" {
  domain_name    = "llm-brand-monitor"
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type          = "r6g.large.search"
    instance_count         = 3
    zone_awareness_enabled = true

    zone_awareness_config {
      availability_zone_count = 3
    }
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = 100
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  vpc_options {
    subnet_ids         = aws_subnet.data[*].id
    security_group_ids = [aws_security_group.opensearch.id]
  }

  tags = {
    Environment = "production"
    Application = "llm-brand-monitor"
  }
}
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: xxxxx.dkr.ecr.us-east-1.amazonaws.com
  EKS_CLUSTER: llm-brand-monitor-cluster

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest tests/ --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push API image
        run: |
          docker build -t $ECR_REGISTRY/llm-brand-monitor/api:${{ github.sha }} -f Dockerfile.api .
          docker push $ECR_REGISTRY/llm-brand-monitor/api:${{ github.sha }}
          docker tag $ECR_REGISTRY/llm-brand-monitor/api:${{ github.sha }} $ECR_REGISTRY/llm-brand-monitor/api:latest
          docker push $ECR_REGISTRY/llm-brand-monitor/api:latest

      - name: Build and push Worker image
        run: |
          docker build -t $ECR_REGISTRY/llm-brand-monitor/worker:${{ github.sha }} -f Dockerfile.worker .
          docker push $ECR_REGISTRY/llm-brand-monitor/worker:${{ github.sha }}
          docker tag $ECR_REGISTRY/llm-brand-monitor/worker:${{ github.sha }} $ECR_REGISTRY/llm-brand-monitor/worker:latest
          docker push $ECR_REGISTRY/llm-brand-monitor/worker:latest

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Update kubeconfig
        run: aws eks update-kubeconfig --name $EKS_CLUSTER-staging

      - name: Deploy to staging
        run: |
          kubectl set image deployment/api-service api=$ECR_REGISTRY/llm-brand-monitor/api:${{ github.sha }} -n llm-brand-monitor
          kubectl set image deployment/celery-worker worker=$ECR_REGISTRY/llm-brand-monitor/worker:${{ github.sha }} -n llm-brand-monitor-jobs
          kubectl rollout status deployment/api-service -n llm-brand-monitor

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID_PROD }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY_PROD }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Update kubeconfig
        run: aws eks update-kubeconfig --name $EKS_CLUSTER-production

      - name: Deploy to production
        run: |
          kubectl set image deployment/api-service api=$ECR_REGISTRY/llm-brand-monitor/api:${{ github.sha }} -n llm-brand-monitor
          kubectl set image deployment/celery-worker worker=$ECR_REGISTRY/llm-brand-monitor/worker:${{ github.sha }} -n llm-brand-monitor-jobs
          kubectl rollout status deployment/api-service -n llm-brand-monitor
```

### Database Migrations

```yaml
# .github/workflows/migrations.yml
name: Database Migrations

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - staging
          - production

jobs:
  migrate:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run migrations
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: alembic upgrade head
```

---

## Monitoring & Observability

### Prometheus Configuration

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)

  - job_name: 'celery'
    static_configs:
      - targets: ['celery-flower:5555']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### Grafana Dashboards

Key dashboards to configure:

1. **API Performance Dashboard**
   - Request rate by endpoint
   - Response latency (p50, p95, p99)
   - Error rate by status code
   - Active connections

2. **LLM Simulation Dashboard**
   - Simulations per hour
   - LLM API latency by provider
   - Token usage by provider
   - Cost tracking

3. **Background Jobs Dashboard**
   - Queue depth
   - Worker utilization
   - Task success/failure rates
   - Average task duration

4. **Database Dashboard**
   - Connection pool utilization
   - Query latency
   - Slow queries
   - Replication lag

### Alerting Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: api-alerts
    rules:
      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is above 5% for the last 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency"
          description: "95th percentile latency is above 2 seconds"

  - name: celery-alerts
    rules:
      - alert: HighQueueDepth
        expr: celery_queue_length > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Celery queue depth is high"
          description: "Queue has more than 1000 pending tasks"

      - alert: WorkerDown
        expr: celery_workers < 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Celery workers are down"
          description: "Less than 5 Celery workers are running"

  - name: database-alerts
    rules:
      - alert: HighConnectionUsage
        expr: pg_stat_activity_count / pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool near capacity"

      - alert: ReplicationLag
        expr: pg_replication_lag > 30
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database replication lag is high"
```

---

## Security

### Network Security

```terraform
# terraform/security_groups.tf
resource "aws_security_group" "api" {
  name_prefix = "llm-brand-monitor-api-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "llm-brand-monitor-rds-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }
}
```

### Secrets Management

```yaml
# kubernetes/secrets.yaml (template - actual values from AWS Secrets Manager)
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
  namespace: llm-brand-monitor
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: app-secrets
  data:
    - secretKey: DATABASE_PASSWORD
      remoteRef:
        key: llm-brand-monitor/database
        property: password
    - secretKey: OPENAI_API_KEY
      remoteRef:
        key: llm-brand-monitor/llm-keys
        property: openai
    - secretKey: ANTHROPIC_API_KEY
      remoteRef:
        key: llm-brand-monitor/llm-keys
        property: anthropic
```

### WAF Rules

```terraform
# terraform/waf.tf
resource "aws_wafv2_web_acl" "main" {
  name  = "llm-brand-monitor-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "RateLimitRule"
    priority = 1

    override_action {
      none {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "RateLimitRule"
      sampled_requests_enabled  = true
    }
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "CommonRuleSet"
      sampled_requests_enabled  = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "llm-brand-monitor-waf"
    sampled_requests_enabled  = true
  }
}
```

---

## Backup & Disaster Recovery

### Backup Strategy

| Component | Backup Frequency | Retention | Recovery Point Objective (RPO) |
|-----------|-----------------|-----------|-------------------------------|
| PostgreSQL | Continuous + Daily snapshots | 30 days | 5 minutes |
| Redis | Hourly snapshots | 7 days | 1 hour |
| Neo4j Aura | Daily (managed) | 30 days | 24 hours |
| OpenSearch | Daily snapshots | 14 days | 24 hours |
| S3 | Cross-region replication | Indefinite | Near-real-time |

### Disaster Recovery

**Recovery Time Objective (RTO):** 4 hours

**DR Strategy:**
1. **Hot Standby** - RDS Multi-AZ provides automatic failover
2. **Warm Standby** - Secondary region with scaled-down infrastructure
3. **Backup/Restore** - S3 cross-region replication for data

### Runbooks

#### Database Failover
```bash
# Force RDS failover (if automatic doesn't trigger)
aws rds reboot-db-instance \
  --db-instance-identifier llm-brand-monitor-db \
  --force-failover

# Verify new primary
aws rds describe-db-instances \
  --db-instance-identifier llm-brand-monitor-db \
  --query 'DBInstances[0].Endpoint'
```

#### Restore from Backup
```bash
# Restore RDS from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier llm-brand-monitor-db-restored \
  --db-snapshot-identifier rds:llm-brand-monitor-db-2024-01-15-03-00

# Update application config to point to restored instance
kubectl set env deployment/api-service \
  DATABASE_HOST=new-db-endpoint.xxxxx.us-east-1.rds.amazonaws.com \
  -n llm-brand-monitor
```

---

## Cost Optimization

### Resource Estimates (Monthly)

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| EKS | Cluster + nodes | $500 |
| RDS PostgreSQL | db.r6g.xlarge, Multi-AZ | $800 |
| ElastiCache Redis | cache.r6g.large x3 | $600 |
| OpenSearch | r6g.large.search x3 | $700 |
| Neo4j Aura | Professional | $400 |
| S3 | 500GB + requests | $50 |
| Data Transfer | ~500GB/month | $50 |
| LLM API Costs | Variable | $2,000-10,000 |
| **Total** | | **$5,100-13,100** |

### Cost Saving Measures

1. **Reserved Instances** - 1-year commitment for RDS, ElastiCache (30-40% savings)
2. **Spot Instances** - For Celery workers (60-70% savings)
3. **LLM Response Caching** - Reduce redundant API calls
4. **Auto-scaling** - Scale down during off-peak hours
5. **S3 Lifecycle Policies** - Move old data to Glacier

```terraform
# terraform/spot_instances.tf
resource "aws_eks_node_group" "spot_workers" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "spot-workers"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = aws_subnet.private[*].id

  capacity_type = "SPOT"

  scaling_config {
    desired_size = 5
    max_size     = 20
    min_size     = 2
  }

  instance_types = ["m5.large", "m5a.large", "m6i.large"]

  labels = {
    "workload-type" = "background-jobs"
  }

  taint {
    key    = "workload-type"
    value  = "background-jobs"
    effect = "NO_SCHEDULE"
  }
}
```

---

## Operational Procedures

### Deployment Checklist

- [ ] All tests passing in CI
- [ ] Database migrations tested in staging
- [ ] Feature flags configured
- [ ] Monitoring alerts reviewed
- [ ] Rollback plan documented
- [ ] On-call engineer notified

### Scaling Procedures

```bash
# Manual scale-up for expected traffic spike
kubectl scale deployment/api-service --replicas=10 -n llm-brand-monitor
kubectl scale deployment/celery-worker --replicas=20 -n llm-brand-monitor-jobs

# Scale down after traffic normalizes
kubectl scale deployment/api-service --replicas=3 -n llm-brand-monitor
kubectl scale deployment/celery-worker --replicas=10 -n llm-brand-monitor-jobs
```

### Log Access

```bash
# View API logs
kubectl logs -l app=api-service -n llm-brand-monitor --tail=100 -f

# View Celery worker logs
kubectl logs -l app=celery-worker -n llm-brand-monitor-jobs --tail=100 -f

# Search logs in CloudWatch
aws logs filter-log-events \
  --log-group-name /aws/eks/llm-brand-monitor/api \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```
