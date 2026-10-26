export function ApiKeyNotice() {
  return (
    <p className="api-key-notice">
      Your API key is used only for this session's requests to your chosen provider. It is
      never written to disk or logged by the backend.
    </p>
  );
}
