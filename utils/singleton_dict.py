#!/usr/bin/env python3
"""
Singleton Dictionary Manager - Provides monitorable global dictionary storage
"""

import threading
import time
from typing import Any, Callable, Dict, List, Optional


class SingletonDictManager:
    """
    Singleton pattern dictionary manager with modification monitoring and logging support
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:  # pylint: disable=access-member-before-definition
            return

        self._initialized = True
        self._data: Dict[str, Dict] = {}
        self._observers: Dict[str, List[Callable]] = {}
        self._modification_history: List[Dict] = []
        self._dict_lock = threading.RLock()  # Support recursive locking

        print("SingletonDictManager initialization completed")

    def get_dict(self, name: str) -> "MonitoredDict":
        """
        Get or create a monitored dictionary

        Args:
            name: Dictionary name

        Returns:
            MonitoredDict: Monitored dictionary object
        """
        with self._dict_lock:
            if name not in self._data:
                self._data[name] = {}
                self._observers[name] = []
                print(f"Creating new monitored dictionary: {name}")

            return MonitoredDict(self, name)

    def add_observer(self, dict_name: str, callback: Callable[[str, str, Any, Any], None]):
        """
        Add modification observer for specified dictionary

        Args:
            dict_name: Dictionary name
            callback: Callback function with signature (dict_name, operation, key, value)
        """
        with self._dict_lock:
            if dict_name not in self._observers:
                self._observers[dict_name] = []
            self._observers[dict_name].append(callback)
            print(f"Adding observer for dictionary {dict_name}")

    def remove_observer(self, dict_name: str, callback: Callable):
        """
        Remove observer
        """
        with self._dict_lock:
            if dict_name in self._observers and callback in self._observers[dict_name]:
                self._observers[dict_name].remove(callback)
                print(f"Removing observer from dictionary {dict_name}")

    def _notify_observers(
        self,
        dict_name: str,
        operation: str,
        key: Any = None,
        value: Any = None,
        old_value: Any = None,
    ):
        """
        Notify all observers that dictionary has been modified
        """
        timestamp = time.time()
        modification_info = {
            "timestamp": timestamp,
            "dict_name": dict_name,
            "operation": operation,
            "key": key,
            "value": value,
            "old_value": old_value,
        }

        # Record modification history
        self._modification_history.append(modification_info)

        # Limit history record count
        if len(self._modification_history) > 1000:
            self._modification_history = self._modification_history[-500:]

        # Log records
        if operation in ["set", "update"]:
            print(
                f"Dictionary modification [{dict_name}]: {operation} key='{key}' value='{value}' (old_value='{old_value}')"
            )
        elif operation == "delete":
            print(f"Dictionary modification [{dict_name}]: {operation} key='{key}' (old_value='{old_value}')")
        elif operation == "clear":
            print(f"Dictionary modification [{dict_name}]: {operation} (cleared all items)")
        else:
            print(f"Dictionary modification [{dict_name}]: {operation}")

        # Notify observers
        if dict_name in self._observers:
            # Copy list to avoid modification conflicts
            for observer in self._observers[dict_name][:]:
                try:
                    observer(dict_name, operation, key, value, old_value)
                except Exception as e:
                    print(f"Observer callback failed: {e}")

    def get_modification_history(self, dict_name: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Get modification history

        Args:
            dict_name: Dictionary name, None means get history for all dictionaries
            limit: Limit on number of records returned

        Returns:
            Modification history list
        """
        with self._dict_lock:
            history = self._modification_history
            if dict_name:
                history = [h for h in history if h["dict_name"] == dict_name]
            return history[-limit:] if limit > 0 else history

    def clear_history(self, dict_name: Optional[str] = None):
        """
        Clear modification history
        """
        with self._dict_lock:
            if dict_name:
                self._modification_history = [h for h in self._modification_history if h["dict_name"] != dict_name]
                print(f"Clearing modification history for dictionary {dict_name}")
            else:
                self._modification_history.clear()
                print("Clearing modification history for all dictionaries")

    def get_all_dict_names(self) -> List[str]:
        """
        Get all dictionary names
        """
        with self._dict_lock:
            return list(self._data.keys())

    def get_dict_info(self, dict_name: str) -> Dict:
        """
        Get dictionary information
        """
        with self._dict_lock:
            if dict_name not in self._data:
                return {"exists": False}

            return {
                "exists": True,
                "size": len(self._data[dict_name]),
                "keys": list(self._data[dict_name].keys()),
                "observers_count": len(self._observers.get(dict_name, [])),
            }


class MonitoredDict:
    """
    Monitored dictionary class, all operations are logged and observers are notified
    """

    def __init__(self, manager: SingletonDictManager, name: str):
        self._manager = manager
        self._name = name

    @property
    def _data(self):
        return self._manager._data[self._name]

    def __getitem__(self, key):
        with self._manager._dict_lock:
            return self._data[key]

    def __setitem__(self, key, value):
        with self._manager._dict_lock:
            old_value = self._data.get(key)
            self._data[key] = value
            self._manager._notify_observers(self._name, "set", key, value, old_value)

    def __delitem__(self, key):
        with self._manager._dict_lock:
            old_value = self._data.get(key)
            del self._data[key]
            self._manager._notify_observers(self._name, "delete", key, None, old_value)

    def __contains__(self, key):
        with self._manager._dict_lock:
            return key in self._data

    def __len__(self):
        with self._manager._dict_lock:
            return len(self._data)

    def __iter__(self):
        with self._manager._dict_lock:
            # Return copy of keys to avoid concurrent modification issues
            return iter(list(self._data.keys()))

    def keys(self):
        with self._manager._dict_lock:
            return self._data.keys()

    def values(self):
        with self._manager._dict_lock:
            return self._data.values()

    def items(self):
        with self._manager._dict_lock:
            return self._data.items()

    def get(self, key, default=None):
        with self._manager._dict_lock:
            return self._data.get(key, default)

    def pop(self, key, *args):
        with self._manager._dict_lock:
            old_value = self._data.get(key)
            result = self._data.pop(key, *args)
            if key in self._data or len(args) == 0:  # If key exists or no default value
                self._manager._notify_observers(self._name, "delete", key, None, old_value)
            return result

    def popitem(self):
        with self._manager._dict_lock:
            key, value = self._data.popitem()
            self._manager._notify_observers(self._name, "delete", key, None, value)
            return key, value

    def clear(self):
        with self._manager._dict_lock:
            self._data.clear()
            self._manager._notify_observers(self._name, "clear")

    def update(self, *args, **kwargs):
        with self._manager._dict_lock:
            # Record values before update
            if args:
                if len(args) > 1:
                    raise TypeError(f"update expected at most 1 arguments, got {len(args)}")
                other = args[0]
                if hasattr(other, "items"):
                    for key, value in other.items():
                        old_value = self._data.get(key)
                        self._data[key] = value
                        self._manager._notify_observers(self._name, "update", key, value, old_value)
                else:
                    for key, value in other:
                        old_value = self._data.get(key)
                        self._data[key] = value
                        self._manager._notify_observers(self._name, "update", key, value, old_value)

            for key, value in kwargs.items():
                old_value = self._data.get(key)
                self._data[key] = value
                self._manager._notify_observers(self._name, "update", key, value, old_value)

    def setdefault(self, key, default=None):
        with self._manager._dict_lock:
            if key not in self._data:
                self._data[key] = default
                self._manager._notify_observers(self._name, "set", key, default, None)
            return self._data[key]

    def copy(self):
        with self._manager._dict_lock:
            return self._data.copy()

    def __repr__(self):
        with self._manager._dict_lock:
            return f"MonitoredDict({self._name}): {repr(self._data)}"

    def __str__(self):
        return self.__repr__()


# Create global singleton instance
dict_manager = SingletonDictManager()


# Convenience functions
def get_monitored_dict(name: str) -> MonitoredDict:
    """
    Get monitored dictionary instance

    Args:
        name: Dictionary name

    Returns:
        MonitoredDict: Monitored dictionary
    """
    return dict_manager.get_dict(name)


def add_dict_observer(dict_name: str, callback: Callable[[str, str, Any, Any], None]):
    """
    Add observer for dictionary

    Args:
        dict_name: Dictionary name
        callback: Callback function
    """
    dict_manager.add_observer(dict_name, callback)


def get_dict_history(dict_name: str = None, limit: int = 100) -> List[Dict]:
    """
    Get dictionary modification history

    Args:
        dict_name: Dictionary name, None means all dictionaries
        limit: Limit on number of records returned

    Returns:
        Modification history list
    """
    return dict_manager.get_modification_history(dict_name, limit)
