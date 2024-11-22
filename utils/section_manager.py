import pandas as pd
from typing import Dict, List
import logging
import os
from config import SECTION_CONFIG_FILE
from utils import database


class SectionManager:
    def __init__(
        self,
        config_file: str = SECTION_CONFIG_FILE,
    ):
        """
        Initialize the section manager with configuration file and database connection.

        Args:
            config_file (str): Path to the Excel configuration file
        """
        self.config_file = config_file
        self.section_config: Dict = {}
        self.load_config()

    def get_user_count(self) -> int:
        """Get the total number of users from the database."""
        try:
            return database.execute_query(
                "SELECT COUNT(*) FROM users", commit=False, fetch_one=True
            )[0][0]
        except Exception as e:
            logging.error(f"Error getting user count: {e}")
            return 0

    def load_config(self) -> None:
        """Load section configuration from Excel file and check user thresholds."""
        try:
            if not os.path.exists(self.config_file):
                print("true")
                # self._create_default_config()

            df = pd.read_excel(self.config_file)
            user_count = self.get_user_count()
            self.section_config = {}

            for _, row in df.iterrows():
                section_path = row["section_path"]
                unlock_threshold = row["unlock_threshold"]

                # Auto-unlock section if user count meets threshold
                is_available = bool(row["is_available"]) or (
                    unlock_threshold > 0 and user_count >= unlock_threshold
                )

                self.section_config[section_path] = {
                    "is_available": is_available,
                    "maintenance_message": row["maintenance_message"],
                    "unlock_threshold": unlock_threshold,
                    "current_users": user_count,
                }

                # Update Excel file if section was auto-unlocked
                if is_available and not bool(row["is_available"]):
                    self._update_section_availability(section_path, True)

            logging.info("Section configuration loaded successfully")
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            # self._create_default_config()

    def _update_section_availability(
        self, section_path: str, is_available: bool
    ) -> None:
        """Update the availability status in the Excel file."""
        try:
            df = pd.read_excel(self.config_file)
            df.loc[df["section_path"] == section_path, "is_available"] = is_available
            df.to_excel(self.config_file, index=False)
            logging.info(f"Updated availability for {section_path} to {is_available}")
        except Exception as e:
            logging.error(f"Error updating section availability: {e}")

    def _create_default_config(self) -> None:
        """Create default configuration file with unlock thresholds."""
        default_config = {
            "section_path": [
                "traditional_learning",
                "traditional_learning:verbal",
                "traditional_learning:quantitative",
            ],
            "is_available": [True, True, False],
            "unlock_threshold": [0, 0, 1000],
            "maintenance_message": [
                "سيتم فتح هذا القسم تلقائياً",
                "سيتم فتح هذا القسم تلقائياً",
                "سيتم فتح هذا القسم تلقائياً عند وصول عدد المستخدمين إلى {threshold} مستخدم 🚧\nالعدد الحالي: {current} مستخدم",
            ],
        }
        df = pd.DataFrame(default_config)
        df.to_excel(self.config_file, index=False)
        self.section_config = {
            path: {
                "is_available": avail,
                "unlock_threshold": thresh,
                "maintenance_message": maint,
            }
            for path, avail, thresh, maint in zip(
                default_config["section_path"],
                default_config["is_available"],
                default_config["unlock_threshold"],
                default_config["maintenance_message"],
            )
        }

    def is_section_available(self, section_path: str) -> bool:
        """
        Check if a section is available.

        Args:
            section_path (str): Section identifier (e.g., 'traditional_learning:quantitative')

        Returns:
            bool: True if section is available, False otherwise
        """
        return self.section_config.get(section_path, {}).get("is_available", True)

    def get_section_message(self, section_path: str) -> str:
        """Get the appropriate message for a section, including user count progress."""
        config = self.section_config.get(section_path, {})
        if not config.get("is_available", False):
            return config.get("maintenance_message", "").format(
                threshold=config.get("unlock_threshold", 0),
                current=config.get("current_users", 0),
            )

    def check_and_update_thresholds(self) -> List[str]:
        """
        Check if any sections should be unlocked based on current user count.
        Returns list of newly unlocked sections.
        """
        user_count = self.get_user_count()
        newly_unlocked = []

        for section_path, config in self.section_config.items():
            if not config["is_available"] and config["unlock_threshold"] > 0:
                if user_count >= config["unlock_threshold"]:
                    self._update_section_availability(section_path, True)
                    newly_unlocked.append(section_path)
                    self.section_config[section_path]["is_available"] = True

        return newly_unlocked


section_manager = SectionManager()


# Check for newly unlocked sections (you can do this periodically)
async def check_unlocked_sections():
    newly_unlocked = section_manager.check_and_update_thresholds()
    if newly_unlocked:
        # Optionally notify users about newly unlocked sections
        pass
