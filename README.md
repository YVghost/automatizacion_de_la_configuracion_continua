# Pedal Club Â· GitOps

Proyecto individual de **Mateo Ortega**. API FastAPI y panel web para registrar bicicletas y compartir reseÃ±as de accesorios con fotos PNG/JPEG (mÃ¡ximo 2 MB) y puntuaciones de 1 a 5.

## Desarrollo local

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload
```

Panel: http://127.0.0.1:8000 Â· OpenAPI: http://127.0.0.1:8000/docs

SQLite se utiliza Ãºnicamente en desarrollo local. Kubernetes utiliza PostgreSQL y un PVC, compartidos por todas las rÃ©plicas. Las fotos se almacenan en la base de datos. Es una demostraciÃ³n acadÃ©mica sin autenticaciÃ³n; utiliza datos ficticios.

## Kubernetes y Argo CD

Requisitos: Docker Desktop encendido con contenedores Linux, minikube, kubectl y repositorio pÃºblico accesible. El script utiliza el contexto minikube. CompruÃ©balo antes de ejecutar.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
kubectl get applications -n argocd
kubectl get pods,svc,hpa -n pedal-club
kubectl top pods -n pedal-club
minikube service pedal-club -n pedal-club --url
```

MantÃ©n abierto el tÃºnel de `minikube service` en Windows. El Service es NodePort 30080, puerto 80 y targetPort 8000. Otra opciÃ³n para revisar el panel es `kubectl port-forward -n pedal-club service/pedal-club 8000:80`; esta Ãºltima comprueba el Service, pero no el acceso NodePort.

`k8s/` contiene exclusivamente los tres manifiestos de la entrega:

| Archivo | ConfiguraciÃ³n |
| --- | --- |
| deployment.yml | 2 rÃ©plicas iniciales; label/selector app=pedal-club; puerto 8000; requests 100m/128Mi; limits 500m/256Mi |
| service.yml | NodePort 30080 â†’ 80 â†’ 8000; selector app=pedal-club |
| hpa.yml | autoscaling/v2; Deployment pedal-club; mÃ­nimo 2, mÃ¡ximo 5; CPU 50% |

`infra/postgres.yml` y el Secret se preparan antes de la aplicaciÃ³n. El Secret se genera localmente y no se publica. `argocd/application.yml` apunta a la rama main y ruta k8s del repositorio pÃºblico. Automated Sync activa prune y selfHeal. `/spec/replicas` se ignora con RespectIgnoreDifferences para permitir que el HPA gestione el escalamiento.

Para entrar a Argo CD: `kubectl port-forward svc/argocd-server -n argocd 8080:443`, abrir https://localhost:8080, usuario admin. ObtÃ©n la contraseÃ±a inicial localmente desde el Secret `argocd-initial-admin-secret`; no la incluyas en las capturas.

## Imagen y cambios GitOps

La prÃ¡ctica carga la imagen local en minikube. El workflow de GitHub Actions permite publicarla en GHCR al crear un tag `v*` o ejecutarlo manualmente; revisa que el paquete sea pÃºblico antes de usar otro clÃºster. No es necesario GHCR para la prÃ¡ctica local.

Para verificar sincronizaciÃ³n automÃ¡tica cambia una anotaciÃ³n del Pod en deployment.yml, realiza commit y push y observa Argo CD. Para cambios del cÃ³digo construye una nueva imagen con una etiqueta nueva, cÃ¡rgala en minikube y actualiza `image` en Git; evita reutilizar etiquetas.

## Verificar escalamiento

```powershell
kubectl top pods -n pedal-club
kubectl apply -f scripts/load-test.yml
kubectl get hpa,pods -n pedal-club -w
# Tras observar el incremento, en otra terminal:
kubectl delete job pedal-load -n pedal-club
kubectl get hpa,pods -n pedal-club -w
```

La carga dura 210 segundos y termina como mÃ¡ximo a los 240. Espera varios minutos para observar el retorno a 2 rÃ©plicas. El objetivo de CPU es relativo al request de 100m (50% = 50m por Pod). El endpoint de carga se habilita solamente para esta prÃ¡ctica con ENABLE_LOAD_TEST=true; desactÃ­valo al terminar.

## ValidaciÃ³n y entrega

```powershell
python -m pytest -q
git check-ignore entregables/Informe_Mateo_Ortega.docx entregables/evidencias/captura.png
```

El informe y las capturas se guardan Ãºnicamente en `entregables/`, excluido de Git y del contexto Docker. El informe debe distinguir las verificaciones ejecutadas de las pendientes. No publicar contraseÃ±as ni capturas de Secrets.

Referencias: [HPA Kubernetes](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/), [Automated Sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/), [RespectIgnoreDifferences](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/).

