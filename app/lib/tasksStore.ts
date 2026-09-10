export const tasksStore = (globalThis as any).tasksStore || new Map<string, any>();
if (process.env.NODE_ENV !== 'production') {
  (globalThis as any).tasksStore = tasksStore;
}
