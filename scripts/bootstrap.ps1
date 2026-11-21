$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Check { if ($LASTEXITCODE -ne 0) { throw 'El comando anterior falló.' } }
minikube start
Check
minikube addons enable metrics-server
Check
kubectl create namespace pedal-club --dry-run=client -o yaml | kubectl apply -f -
Check
# The generated password is sent through stdin; it is never saved to Git or printed.
$password = [guid]::NewGuid().ToString('N')
$secret = @{apiVersion='v1';kind='Secret';metadata=@{name='pedal-db';namespace='pedal-club'};type='Opaque';stringData=@{password=$password;url="postgresql+psycopg://pedal:$password@postgres:5432/pedal"}}
$existingSecret = kubectl get secret pedal-db -n pedal-club -o name --ignore-not-found
Check
if (-not $existingSecret) { $secret | ConvertTo-Json -Depth 6 -Compress | kubectl apply -f -; Check }
kubectl apply -f infra/postgres.yml
Check
kubectl rollout status deployment/postgres -n pedal-club --timeout=180s
Check
# For the local minikube practice, preload exactly the image referenced in Git.
docker build -t ghcr.io/yvghost/automatizacion_de_la_configuracion_continua:1.0.0 .
Check
minikube image load ghcr.io/yvghost/automatizacion_de_la_configuracion_continua:1.0.0
Check
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
Check
kubectl apply --server-side -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.2.1/manifests/install.yaml
Check
kubectl rollout status deployment/argocd-server -n argocd --timeout=300s
Check
kubectl apply -f argocd/application.yml
Check
Write-Host 'Aplicación creada. Comprueba: kubectl get applications -n argocd; kubectl get pods,svc,hpa -n pedal-club'
