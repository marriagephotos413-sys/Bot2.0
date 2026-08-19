import asyncio
import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(
    "telegram-test-series-bot.backup"
)


# ============================================================
# BACKUP SERVICE
# ============================================================

class BackupService:
    """
    Backup manager.

    Backup में:
    - MongoDB data
    - Bot settings
    - Pricing
    - Channel configuration
    - Reports
    - Local metadata

    शामिल किए जा सकते हैं।

    IMPORTANT:
    Test JSON MongoDB में store नहीं किया जाएगा।
    Test JSON GitHub की tcs.html में रहेगा।
    इसलिए backup service test JSON को MongoDB से export
    करने की कोशिश नहीं करती।
    """

    def __init__(
        self,
        backup_dir: Optional[str] = None,
    ):

        self.backup_dir = Path(
            backup_dir
            or os.getenv(
                "BACKUP_DIR",
                "./backups",
            )
        )

        self.backup_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.running = False

        self.last_backup: Optional[
            Dict[str, Any]
        ] = None

    # ========================================================
    # TIMESTAMP
    # ========================================================

    @staticmethod
    def timestamp() -> str:

        return datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%d_%H%M%S"
        )

    # ========================================================
    # BACKUP NAME
    # ========================================================

    def backup_path(
        self,
        prefix: str = "bot_backup",
    ) -> Path:

        return (
            self.backup_dir
            / f"{prefix}_{self.timestamp()}.zip"
        )

    # ========================================================
    # EXPORT DATABASE
    # ========================================================

    async def export_database(
        self,
        destination: Path,
    ) -> Dict[str, Any]:

        """
        Database module से export करने की कोशिश।

        Database implementation के अनुसार common
        export methods support किए गए हैं।
        """

        database_data: Any = {}

        try:

            from app.database import db

        except Exception as exc:

            logger.exception(
                "Database import failed."
            )

            return {
                "success": False,
                "error": str(exc),
            }

        try:

            export_methods = (
                "export_backup",
                "export_data",
                "backup",
                "dump_data",
            )

            for method_name in export_methods:

                method = getattr(
                    db,
                    method_name,
                    None,
                )

                if not method:
                    continue

                try:

                    result = method()

                    if hasattr(
                        result,
                        "__await__",
                    ):

                        result = await result

                    database_data = (
                        result
                        if result is not None
                        else {}
                    )

                    break

                except TypeError:

                    continue

            output = (
                destination
                / "database.json"
            )

            output.write_text(
                json.dumps(
                    database_data,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

            return {
                "success": True,
                "file": str(output),
            }

        except Exception as exc:

            logger.exception(
                "Database export failed."
            )

            return {
                "success": False,
                "error": str(exc),
            }

    # ========================================================
    # EXPORT CONFIGURATION
    # ========================================================

    async def export_configuration(
        self,
        destination: Path,
    ) -> Dict[str, Any]:

        config: Dict[str, Any] = {}

        # ----------------------------------------------------
        # Channels
        # ----------------------------------------------------

        try:

            from app.channels import (
                channel_service,
            )

            config["channels"] = (
                channel_service.list_channels(
                    enabled_only=False
                )
            )

        except Exception:

            logger.debug(
                "Channel configuration export skipped.",
                exc_info=True,
            )

        # ----------------------------------------------------
        # Force Join
        # ----------------------------------------------------

        try:

            from app.force_join import (
                force_join_service,
            )

            config["force_join"] = (
                force_join_service.list_channels(
                    enabled_only=False
                )
            )

        except Exception:

            logger.debug(
                "Force join export skipped.",
                exc_info=True,
            )

        # ----------------------------------------------------
        # Pricing
        # ----------------------------------------------------

        try:

            from app.pricing import (
                pricing_service,
            )

            config["pricing"] = (
                pricing_service.get_plans(
                    enabled_only=False
                )
            )

        except Exception:

            logger.debug(
                "Pricing export skipped.",
                exc_info=True,
            )

        # ----------------------------------------------------
        # Free Trial
        # ----------------------------------------------------

        try:

            from app.free_trial import (
                free_trial,
            )

            config["free_trial"] = {
                "locked": (
                    free_trial.is_locked()
                ),
                "default_days": (
                    free_trial.default_days
                ),
            }

        except Exception:

            logger.debug(
                "Free trial export skipped.",
                exc_info=True,
            )

        output = (
            destination
            / "configuration.json"
        )

        output.write_text(
            json.dumps(
                config,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        return {
            "success": True,
            "file": str(output),
        }

    # ========================================================
    # EXPORT METADATA
    # ========================================================

    async def export_metadata(
        self,
        destination: Path,
    ) -> Dict[str, Any]:

        metadata = {
            "backup_created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "version": "1.0",
            "note": (
                "Test JSON is not stored in MongoDB. "
                "Test data is maintained in GitHub tcs.html."
            ),
        }

        output = (
            destination
            / "backup_metadata.json"
        )

        output.write_text(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return {
            "success": True,
            "file": str(output),
        }

    # ========================================================
    # CREATE BACKUP
    # ========================================================

    async def create_backup(
        self,
        prefix: str = "bot_backup",
    ) -> Dict[str, Any]:

        if self.running:

            return {
                "success": False,
                "error": (
                    "Another backup is already running."
                ),
            }

        self.running = True

        zip_path = self.backup_path(
            prefix
        )

        temporary_dir = Path(
            tempfile.mkdtemp(
                prefix="telegram_bot_backup_"
            )
        )

        try:

            # ------------------------------------------------
            # Database
            # ------------------------------------------------

            database_result = (
                await self.export_database(
                    temporary_dir
                )
            )

            # ------------------------------------------------
            # Configuration
            # ------------------------------------------------

            config_result = (
                await self.export_configuration(
                    temporary_dir
                )
            )

            # ------------------------------------------------
            # Metadata
            # ------------------------------------------------

            metadata_result = (
                await self.export_metadata(
                    temporary_dir
                )
            )

            # ------------------------------------------------
            # Create ZIP
            # ------------------------------------------------

            with zipfile.ZipFile(
                zip_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:

                for file_path in (
                    temporary_dir.rglob("*")
                ):

                    if not file_path.is_file():
                        continue

                    archive.write(
                        file_path,
                        arcname=file_path.relative_to(
                            temporary_dir
                        ),
                    )

            size = zip_path.stat().st_size

            result = {
                "success": True,
                "path": str(
                    zip_path
                ),
                "filename": zip_path.name,
                "size": size,
                "database": database_result,
                "configuration": config_result,
                "metadata": metadata_result,
            }

            self.last_backup = result

            logger.info(
                "Backup created: %s",
                zip_path,
            )

            return result

        except Exception as exc:

            logger.exception(
                "Backup creation failed."
            )

            return {
                "success": False,
                "error": str(exc),
            }

        finally:

            self.running = False

            try:

                shutil.rmtree(
                    temporary_dir,
                    ignore_errors=True,
                )

            except Exception:

                logger.debug(
                    "Temporary backup cleanup failed.",
                    exc_info=True,
                )

    # ========================================================
    # LIST BACKUPS
    # ========================================================

    def list_backups(
        self,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:

        files = []

        for path in sorted(
            self.backup_dir.glob(
                "*.zip"
            ),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):

            try:

                stat = path.stat()

                files.append(
                    {
                        "filename": path.name,
                        "path": str(path),
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(
                            stat.st_mtime,
                            timezone.utc,
                        ),
                    }
                )

            except OSError:

                continue

            if len(files) >= max(
                1,
                int(limit),
            ):

                break

        return files

    # ========================================================
    # DELETE BACKUP
    # ========================================================

    def delete_backup(
        self,
        filename: str,
    ) -> bool:

        filename = os.path.basename(
            filename
        )

        path = (
            self.backup_dir
            / filename
        )

        if not path.exists():

            return False

        if path.suffix.lower() != ".zip":

            return False

        try:

            path.unlink()

            logger.info(
                "Backup deleted: %s",
                filename,
            )

            return True

        except OSError:

            logger.exception(
                "Backup deletion failed."
            )

            return False

    # ========================================================
    # CLEAN OLD BACKUPS
    # ========================================================

    def cleanup_old_backups(
        self,
        keep: int = 10,
    ) -> int:

        keep = max(
            1,
            int(keep),
        )

        backups = self.list_backups(
            limit=10000
        )

        deleted = 0

        for backup in backups[
            keep:
        ]:

            if self.delete_backup(
                backup["filename"]
            ):

                deleted += 1

        return deleted

    # ========================================================
    # BACKUP STATUS
    # ========================================================

    def status(
        self,
    ) -> Dict[str, Any]:

        backups = self.list_backups(
            limit=100
        )

        total_size = sum(
            item["size"]
            for item in backups
        )

        return {
            "running": self.running,
            "count": len(backups),
            "total_size": total_size,
            "last_backup": self.last_backup,
        }

    # ========================================================
    # STATUS TEXT
    # ========================================================

    def status_text(
        self,
    ) -> str:

        data = self.status()

        status = (
            "🟢 RUNNING"
            if data["running"]
            else "⚪ IDLE"
        )

        last_backup = (
            data.get(
                "last_backup"
            )
            or {}
        )

        last_name = (
            last_backup.get(
                "filename"
            )
            or "None"
        )

        return (
            "💾 <b>BACKUP STATUS</b>\n"
            "\n"
            f"📌 Status: {status}\n"
            f"📦 Total Backups: "
            f"<b>{data['count']}</b>\n"
            f"🗂 Last Backup: "
            f"<code>{last_name}</code>\n"
            "\n"
            "ℹ️ Test JSON MongoDB में नहीं है।\n"
            "📄 Test data GitHub के "
            "<code>tcs.html</code> में maintain होगा।"
        )

    # ========================================================
    # RESTORE BACKUP
    # ========================================================

    async def restore_backup(
        self,
        backup_file: str,
    ) -> Dict[str, Any]:

        """
        Backup restore.

        Database restore तभी किया जाएगा जब database module
        explicitly restore/import method provide करता हो।
        """

        path = Path(
            backup_file
        )

        if not path.exists():

            return {
                "success": False,
                "error": "Backup file not found.",
            }

        if path.suffix.lower() != ".zip":

            return {
                "success": False,
                "error": "Invalid backup format.",
            }

        temporary_dir = Path(
            tempfile.mkdtemp(
                prefix="telegram_bot_restore_"
            )
        )

        try:

            with zipfile.ZipFile(
                path,
                "r",
            ) as archive:

                archive.extractall(
                    temporary_dir
                )

            database_file = (
                temporary_dir
                / "database.json"
            )

            if database_file.exists():

                try:

                    from app.database import (
                        db,
                    )

                    restore_method = None

                    for method_name in (
                        "restore_backup",
                        "import_data",
                        "restore_data",
                    ):

                        method = getattr(
                            db,
                            method_name,
                            None,
                        )

                        if method:

                            restore_method = (
                                method
                            )

                            break

                    if restore_method:

                        data = json.loads(
                            database_file.read_text(
                                encoding="utf-8"
                            )
                        )

                        result = restore_method(
                            data
                        )

                        if hasattr(
                            result,
                            "__await__",
                        ):

                            await result

                except Exception:

                    logger.exception(
                        "Database restore failed."
                    )

            return {
                "success": True,
                "restored_from": str(
                    path
                ),
            }

        except Exception as exc:

            logger.exception(
                "Backup restore failed."
            )

            return {
                "success": False,
                "error": str(exc),
            }

        finally:

            shutil.rmtree(
                temporary_dir,
                ignore_errors=True,
            )


# ============================================================
# GLOBAL INSTANCE
# ============================================================

backup_service = BackupService()


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def create_backup(
    prefix: str = "bot_backup",
):

    return await backup_service.create_backup(
        prefix
    )


def list_backups(
    limit: int = 50,
):

    return backup_service.list_backups(
        limit
    )


def delete_backup(
    filename: str,
):

    return backup_service.delete_backup(
        filename
    )


def cleanup_old_backups(
    keep: int = 10,
):

    return backup_service.cleanup_old_backups(
        keep
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "BackupService",
    "backup_service",
    "create_backup",
    "list_backups",
    "delete_backup",
    "cleanup_old_backups",
]
