import { MAX_MESSAGE_CHARS } from "./teamChat.js";

export const PENDING_TASK_KEY = "shimpz_pending_task";
export const MAX_PENDING_TASK_CHARS = MAX_MESSAGE_CHARS;

/** @param {Storage} storage @param {string} value */
export function savePendingTask(storage, value) {
  const task = value.trim();
  if (!task || task.length > MAX_PENDING_TASK_CHARS) return false;
  storage.setItem(PENDING_TASK_KEY, task);
  return true;
}

/** @param {Storage} storage */
export function takePendingTask(storage) {
  const value = storage.getItem(PENDING_TASK_KEY);
  storage.removeItem(PENDING_TASK_KEY);
  if (typeof value !== "string") return "";
  const task = value.trim();
  return task && task.length <= MAX_PENDING_TASK_CHARS ? task : "";
}
