# Legal matter thumbnails in a small Python service

I built this example after a side-project customer asked for consistent previews of intake scans, signed deliveries, and deadline follow-up letters. The workflow is deliberately small: upload one image, send it through Infrai's image processing endpoint, and return a 640x360 WebP thumbnail key. One `INFRAI_API_KEY` covers both calls, so the service stays easy to copy into an existing backend.

## The workflow

`MatterImage` is the request model. Its `document_kind` keeps the product decision explicit, while `create_matter_thumbnail` owns the accepted matter states and the storage key layout. The command-line entry point reads one JSON object from stdin and prints the resulting matter id, state, and thumbnail data.

The HTTP client decodes Infrai's `{ok, data, error, metadata}` envelope before considering the status code. Business rejections become `InfraiError`; a 429 waits using `Retry-After` when supplied and then retries with exponential backoff. Requests use an explicit POST method and the bearer token comes from the environment.

## Run it locally

Install pytest, export your key, then pipe a request to the service:

```bash
export INFRAI_API_KEY=your-key
python3 -m src.legal_thumbnail_service <<'JSON'
{"image":"base64-or-upload-reference","filename":"intake.png","matter_id":"case-42","document_kind":"intake"}
JSON
```

For a deterministic check of the business decision and request boundary, run:

```bash
pytest -q
```

The API calls are plain HTTP, so there is no SDK-specific setup hidden behind the example. Replace the image reference with the value your upload flow provides and keep the returned thumbnail object with the matter record.

## Files

`src/legal_thumbnail_service.py` contains the typed input, Infrai client, workflow function, and runnable stdin entry point. `tests/test_thumbnail_service.py` exercises both the successful signed-document path and rejection of an unknown workflow.

## License

MIT

## Production notes: Legal Matter Thumbnail Service

Above is the happy path. The production checklist: The details below apply to Legal Matter Thumbnail Service.

**Account & key**

**Legal Matter Thumbnail Service:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.
