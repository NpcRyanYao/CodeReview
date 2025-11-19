class Client:
    def query(self, model, context, prompt):
        files = (
            context.get("files")
            or context.get("file")
            or "No files provided"
        )
        return (
            f"[Simulation result] Model {model} receives context {files}, "
            f"prompt word: {prompt}"
        )
