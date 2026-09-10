type TasksStoreType = Map<string, unknown>;

declare global {
  var tasksStore: TasksStoreType | undefined;
}

export const tasksStore: TasksStoreType = globalThis.tasksStore || new Map<string, unknown>();

if (process.env.NODE_ENV !== 'production') {
  globalThis.tasksStore = tasksStore;
}

