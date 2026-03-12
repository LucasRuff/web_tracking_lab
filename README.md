# Self-hosting Web Tracking Lab

Docker containerization is the recommended solution for running this server, and the DockerHub image at https://hub.docker.com/repository/docker/lucasruff/web_tracking_lab/ is the only tested and guaranteed solution. You may serve the container using a solution provided by your school's infrastructure, or you can host the server in a cloud environment. Steps for hosting using Google Cloud Run are provided for convenience.

# Hosting Web Tracking Lab on Google Cloud Run

This guide shows how to deploy the Web Tracking Lab using the pre-built Docker image from DockerHub.

## Prerequisites

- A Google Cloud account with billing enabled
- The `gcloud` CLI installed ([install guide](https://cloud.google.com/sdk/docs/install))

## Steps

### 1. Log in to Google Cloud

```bash
gcloud auth login
```

### 2. Set your project

```bash
gcloud config set project YOUR_PROJECT_ID
```

Replace `YOUR_PROJECT_ID` with your actual Google Cloud project ID (create one if it is not already created).

### 3. Deploy to Cloud Run

```bash
gcloud run deploy genAI-web-tracking-lab \
  --image docker.io/lucasruff/web_tracking_lab:latest \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated \
  --port 8080
```

You can change:
- `genAI-web-tracking-lab` — the service name (can be anything)
- `us-east1` — the region (pick one close to you)

### 4. Get your URL

After deployment, Cloud Run will display a URL like:

```
https://web-tracking-lab-XXXXXXXXXX.us-east1.run.app
```

Your server is now live at that URL!

## Endpoints

Once deployed, these endpoints are available:

| Endpoint | Description |
|----------|-------------|
| `/instructor-solution` | The main lab page with tracking demos |
| `/logs` | View collected beacon data |
| `/script.js` | Third-party tracking script |
| `/hover-widget` | Embeddable hover tracking widget |

## Updating the Deployment

To update to a newer version of the image:

```bash
gcloud run deploy web-tracking-lab \
  --image docker.io/lucasruff/web_tracking_lab:latest \
  --region us-east1
```

## Deleting the Service

To remove the deployment and stop incurring charges:

```bash
gcloud run services delete web-tracking-lab --region us-east1
```

## Troubleshooting

**"Permission denied" errors**: Make sure you have the Cloud Run Admin role on your project.

**Container fails to start**: Check the logs with:
```bash
gcloud run services logs read web-tracking-lab --region us-east1
```

**Image not found**: Ensure you can pull the image locally first:
```bash
docker pull lucasruff/web_tracking_lab:latest
```
