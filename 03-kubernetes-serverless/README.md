# Kubernetes e Serverless

## 1. Control Plane vs Data Plane no Kubernetes

### Control Plane
O **Control Plane** é o "cérebro" do cluster Kubernetes, responsável por tomar decisões sobre onde e como executar workloads.

#### Componentes do Control Plane:

1. **API Server** (`kube-apiserver`)
   - Interface REST para todas as operações do cluster
   - Autenticação e autorização de requests
   - Validação e persistência de objetos da API

2. **etcd**
   - Banco de dados key-value distribuído
   - Armazena todo o estado do cluster
   - Fonte da verdade para configurações

3. **Controller Manager** (`kube-controller-manager`)
   - Executa controllers que regulam o estado do cluster
   - Deployment Controller, ReplicaSet Controller, etc.
   - Monitora diferenças entre estado desejado e atual

4. **Scheduler** (`kube-scheduler`)
   - Decide em qual node um Pod deve ser executado
   - Considera recursos, políticas, afinidades, taints/tolerations

### Data Plane
O **Data Plane** é onde os workloads de aplicação realmente executam.

#### Componentes do Data Plane:

1. **kubelet**
   - Agente que executa em cada node
   - Gerencia Pods e containers
   - Reporta status para o API Server

2. **kube-proxy**
   - Proxy de rede em cada node
   - Implementa services e load balancing
   - Gerencia reglas de iptables/IPVS

3. **Container Runtime**
   - Interface CRI (containerd, CRI-O, Docker)
   - Execução efetiva dos containers

### Interação Control Plane ↔ Data Plane

```mermaid
graph TB
    subgraph "Control Plane"
        API[API Server]
        ETCD[(etcd)]
        CM[Controller Manager]
        SCHED[Scheduler]
    end
    
    subgraph "Data Plane - Node 1"
        KB1[kubelet]
        KP1[kube-proxy]
        CR1[Container Runtime]
        POD1[Pods]
    end
    
    subgraph "Data Plane - Node 2"
        KB2[kubelet]
        KP2[kube-proxy]
        CR2[Container Runtime]
        POD2[Pods]
    end
    
    API --> ETCD
    CM --> API
    SCHED --> API
    KB1 --> API
    KB2 --> API
    KB1 --> CR1
    KB2 --> CR2
    CR1 --> POD1
    CR2 --> POD2
```

## 2. O que ocorre quando o Controller-Manager falha?

### Impactos Imediatos

1. **Parada de Reconciliação**
   - Controllers param de funcionar
   - Estado desejado não é mais aplicado
   - Novos recursos não são processados

2. **Recursos Afetados**
   ```yaml
   # Deployments param de escalar
   # ReplicaSets não criam novos Pods
   # Services não atualizam endpoints
   # Namespaces ficam em estado "Terminating"
   # PersistentVolumes não são bound
   ```

### Cenários Específicos

#### Falha do Deployment Controller
```bash
# Cenário: Scale up de um deployment
kubectl scale deployment nginx --replicas=5

# Comportamento:
# ❌ Novos ReplicaSets não são criados
# ❌ Pods existentes continuam rodando
# ❌ Scale operations param de funcionar
```

#### Falha do Node Controller
```bash
# Cenário: Node fica indisponível
# Comportamento:
# ❌ Pods não são evacuados do node com problema
# ❌ Node status não é atualizado
# ❌ Taints não são aplicadas automaticamente
```

### Recuperação e Mitigação

#### 1. Detecção da Falha
```bash
# Verificar status dos componentes
kubectl get componentstatuses

# Logs do controller-manager
kubectl logs -n kube-system controller-manager-pod

# Health check endpoint
curl -k https://localhost:10257/healthz
```

#### 2. Recuperação Automática (HA)
```yaml
# Setup HA com múltiplas réplicas
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kube-controller-manager
spec:
  replicas: 3  # Múltiplos controller-managers
  selector:
    matchLabels:
      component: kube-controller-manager
  template:
    spec:
      containers:
      - name: kube-controller-manager
        command:
        - kube-controller-manager
        - --leader-elect=true  # Leader election
        - --leader-elect-lease-duration=15s
        - --leader-elect-renew-deadline=10s
        - --leader-elect-retry-period=2s
```

#### 3. Recuperação Manual
```bash
# Restart do controller-manager
systemctl restart kube-controller-manager

# Ou em ambiente gerenciado (EKS)
# AWS automaticamente reconstrói o componente
```

### Prevenção

#### Monitoramento Proativo
```yaml
# Prometheus AlertManager rule
- alert: ControllerManagerDown
  expr: up{job="kube-controller-manager"} == 0
  for: 5m
  labels:
    severity: critical
  annotations:
    description: "Controller Manager has been down for more than 5 minutes"
```

#### Health Checks
```bash
#!/bin/bash
# Script de health check
if ! curl -sf http://localhost:10257/healthz; then
  echo "Controller Manager unhealthy"
  systemctl restart kube-controller-manager
fi
```

## 3. Manifests Kubernetes para Microserviço

### Namespace
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: microservice-app
  labels:
    name: microservice-app
    environment: production
```

### Secret para PostgreSQL
```yaml
# postgresql-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgresql-secret
  namespace: microservice-app
type: Opaque
data:
  # Values are base64 encoded
  username: cG9zdGdyZXM=  # postgres
  password: cGFzc3dvcmQxMjM=  # password123
  database: bXlhcHA=  # myapp
  host: cG9zdGdyZXNxbC1zZXJ2aWNl  # postgresql-service
  port: NTQzMg==  # 5432
stringData:
  # Connection string constructed from individual values
  database_url: "postgresql://postgres:password123@postgresql-service:5432/myapp"
```

### ConfigMap
```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: microservice-config
  namespace: microservice-app
data:
  # Application configuration
  APP_ENV: "production"
  LOG_LEVEL: "info"
  CACHE_TTL: "3600"
  MAX_CONNECTIONS: "100"
  TIMEOUT_SECONDS: "30"
  
  # Feature flags
  ENABLE_METRICS: "true"
  ENABLE_TRACING: "true"
  ENABLE_CACHE: "true"
  
  # External service URLs
  REDIS_URL: "redis://redis-service:6379"
  ELASTICSEARCH_URL: "http://elasticsearch-service:9200"
  
  # App specific config file
  app.properties: |
    server.port=8080
    server.shutdown=graceful
    spring.datasource.hikari.maximum-pool-size=20
    spring.jpa.hibernate.ddl-auto=validate
    logging.pattern.console=%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n
```

### ServiceAccount e RBAC
```yaml
# rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: microservice-sa
  namespace: microservice-app
  labels:
    app: microservice
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: microservice-app
  name: microservice-role
rules:
# Allow reading configmaps and secrets in the same namespace
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list"]
# Allow reading own pod information
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
  resourceNames: [] # Restricts to pods with same service account
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: microservice-rolebinding
  namespace: microservice-app
subjects:
- kind: ServiceAccount
  name: microservice-sa
  namespace: microservice-app
roleRef:
  kind: Role
  name: microservice-role
  apiGroup: rbac.authorization.k8s.io
```

### Deployment com 3 Réplicas
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: microservice-deployment
  namespace: microservice-app
  labels:
    app: microservice
    version: v1.0.0
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  selector:
    matchLabels:
      app: microservice
  template:
    metadata:
      labels:
        app: microservice
        version: v1.0.0
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
        kubectl.kubernetes.io/restartedAt: ""
    spec:
      serviceAccountName: microservice-sa
      
      # Security Context
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      
      # Init container para aguardar dependências
      initContainers:
      - name: wait-for-database
        image: postgres:15-alpine
        command:
          - sh
          - -c
          - |
            until pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER; do
              echo "Waiting for database to be ready..."
              sleep 2
            done
            echo "Database is ready!"
        env:
        - name: DB_HOST
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: host
        - name: DB_PORT
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: port
        - name: DB_USER
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: username
      
      containers:
      - name: microservice
        image: myregistry/microservice:v1.0.0
        imagePullPolicy: IfNotPresent
        
        # Security Context para container
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 1000
          capabilities:
            drop:
            - ALL
        
        ports:
        - name: http
          containerPort: 8080
          protocol: TCP
        - name: metrics
          containerPort: 9090
          protocol: TCP
        
        # Environment variables from ConfigMap
        envFrom:
        - configMapRef:
            name: microservice-config
        
        # Environment variables from Secret
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: database_url
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: password
        
        # Resource limits e requests
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        
        # Liveness probe - verifica se container está vivo
        livenessProbe:
          httpGet:
            path: /health/live
            port: http
            scheme: HTTP
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
          successThreshold: 1
        
        # Readiness probe - verifica se container está pronto para receber tráfego
        readinessProbe:
          httpGet:
            path: /health/ready
            port: http
            scheme: HTTP
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
          successThreshold: 1
        
        # Startup probe - para apps que demoram para inicializar
        startupProbe:
          httpGet:
            path: /health/startup
            port: http
            scheme: HTTP
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 30
          successThreshold: 1
        
        # Volume mounts
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: var-log
          mountPath: /var/log
        - name: app-config
          mountPath: /app/config
          readOnly: true
      
      # Volumes
      volumes:
      - name: tmp
        emptyDir: {}
      - name: var-log
        emptyDir: {}
      - name: app-config
        configMap:
          name: microservice-config
          items:
          - key: app.properties
            path: application.properties
      
      # Pod Disruption Budget - garante disponibilidade durante updates
      # Scheduling constraints
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - microservice
              topologyKey: kubernetes.io/hostname
      
      # Tolerations para nodes especiais
      tolerations:
      - key: "app-workload"
        operator: "Equal"
        value: "microservice"
        effect: "NoSchedule"
      
      # Graceful shutdown
      terminationGracePeriodSeconds: 60
      
      # DNS Policy
      dnsPolicy: ClusterFirst
      
      # Restart policy
      restartPolicy: Always
---
# PodDisruptionBudget
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: microservice-pdb
  namespace: microservice-app
spec:
  minAvailable: 2  # Manter sempre pelo menos 2 pods disponíveis
  selector:
    matchLabels:
      app: microservice
```

### Service
```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: microservice-service
  namespace: microservice-app
  labels:
    app: microservice
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
spec:
  type: ClusterIP  # ou LoadBalancer para acesso externo
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
  - name: metrics
    port: 9090
    targetPort: metrics
    protocol: TCP
  selector:
    app: microservice
  sessionAffinity: None
---
# Headless service para service discovery
apiVersion: v1
kind: Service
metadata:
  name: microservice-headless
  namespace: microservice-app
  labels:
    app: microservice
spec:
  clusterIP: None
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
  selector:
    app: microservice
```

### HorizontalPodAutoscaler (HPA)
```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: microservice-hpa
  namespace: microservice-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: microservice-deployment
  minReplicas: 3
  maxReplicas: 10
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
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 2
        periodSeconds: 60
```

### NetworkPolicy
```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: microservice-netpol
  namespace: microservice-app
spec:
  podSelector:
    matchLabels:
      app: microservice
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # Allow ingress from ingress controller
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
  # Allow ingress from prometheus for metrics
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
  egress:
  # Allow egress to PostgreSQL
  - to:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  # Allow egress to Redis
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  # Allow DNS resolution
  - to: []
    ports:
    - protocol: UDP
      port: 53
  # Allow HTTPS outbound (for external APIs)
  - to: []
    ports:
    - protocol: TCP
      port: 443
```

## Resumo dos Manifests

### ✅ Características Implementadas

1. **3 Réplicas**: ✅ Deployment com `replicas: 3`
2. **Secret PostgreSQL**: ✅ Credenciais seguras com base64
3. **ConfigMap**: ✅ Variáveis de ambiente e config files
4. **Probes**: ✅ Liveness, Readiness e Startup probes
5. **RBAC**: ✅ ServiceAccount, Role e RoleBinding mínimos

### 🔒 Segurança Implementada

- SecurityContext com usuário não-root
- ReadOnlyRootFilesystem
- Capabilities dropped
- RBAC com permissões mínimas
- NetworkPolicy para isolamento de rede

### 📊 Observabilidade

- Prometheus metrics endpoint
- Structured logging
- Health check endpoints
- Resource monitoring via HPA

### 🚀 Próxima Seção
Implementação das funções serverless (AWS Lambda/Azure Functions)
