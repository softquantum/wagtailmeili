from django.core.management.base import BaseCommand
from wagtail.search.backends import get_search_backend
from wagtail.search.index import get_indexed_models


class Command(BaseCommand):
    help = "Clean up stale documents from MeiliSearch index"

    def add_arguments(self, parser):
        parser.add_argument(
            "--backend",
            default="default",
            help='Search backend to clean up (default: "default")',
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--model", help="Only clean up specific model (format: app_label.ModelName)"
        )

    def handle(self, *args, **options):
        self.verbosity = options.get("verbosity", 1)

        backend = get_search_backend(options["backend"])

        if not hasattr(backend, "get_index_for_model"):
            self.stdout.write(
                self.style.ERROR(
                    f"Backend '{options['backend']}' does not support index cleanup"
                )
            )
            return

        models_to_clean = []

        if options["model"]:
            # Parse specific model - handle both app.model and app_label.ModelName formats
            try:
                parts = options["model"].split(".")
                if len(parts) == 3:
                    # Format: app_label.submodule.ModelName
                    app_label = ".".join(parts[:-1])
                    model_name = parts[-1]
                else:
                    # Format: app_label.ModelName
                    app_label, model_name = parts

                from django.apps import apps

                model = apps.get_model(app_label, model_name)
                models_to_clean = [model]
            except (ValueError, LookupError) as e:
                self.stdout.write(
                    self.style.ERROR(f"Invalid model '{options['model']}': {e}")
                )
                return
        else:
            # Get all indexed models
            models_to_clean = get_indexed_models()

        total_cleaned = 0

        for model in models_to_clean:
            cleaned_count = self.cleanup_model_index(backend, model, options["dry_run"])
            total_cleaned += cleaned_count

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run complete. Would have cleaned {total_cleaned} stale documents."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully cleaned {total_cleaned} stale documents."
                )
            )

    def cleanup_model_index(self, backend, model, dry_run=False):
        """Clean up index for a specific model."""
        try:
            index = backend.get_index_for_model(model)
            if index is None:
                self.stdout.write(f"No index found for {model.__name__}, skipping")
                return 0
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Error getting index for {model.__name__}: {e}")
            )
            return 0

        try:
            # Get live objects from database
            if hasattr(model, "live"):
                # For pages, only include live ones
                live_objects = model.objects.filter(live=True)
            else:
                # For other models, include all
                live_objects = model.objects.all()

            live_pks = set(live_objects.values_list("pk", flat=True))

            # Get current index documents
            try:
                current_docs = index.index.get_documents(fields=["id"])
                current_index_ids = {doc["id"] for doc in current_docs.results}
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"Error getting index documents for {model.__name__}: {e}"
                    )
                )
                return 0

            # Convert live_pks to strings for comparison (MeiliSearch uses string IDs)
            live_ids_str = {str(pk) for pk in live_pks}

            # Find stale documents
            stale_ids = current_index_ids - live_ids_str

            if stale_ids:
                if dry_run:
                    self.stdout.write(
                        f"Would delete {len(stale_ids)} stale documents from {model.__name__} index"
                    )
                    if self.verbosity >= 2:
                        for doc_id in sorted(stale_ids):
                            self.stdout.write(f"  - {model.__name__} {doc_id}")
                else:
                    index.bulk_delete_items(list(stale_ids))
                    self.stdout.write(
                        f"Deleted {len(stale_ids)} stale documents from {model.__name__} index"
                    )
                return len(stale_ids)
            else:
                if self.verbosity >= 1:
                    self.stdout.write(f"No stale documents found for {model.__name__}")
                return 0

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error cleaning up {model.__name__}: {e}")
            )
            return 0
