/**
 * WatermelonDB schema — mirrors the backend models we need offline.
 */
import { appSchema, tableSchema } from '@nozbe/watermelondb';

export default appSchema({
  version: 1,
  tables: [
    tableSchema({
      name: 'modules',
      columns: [
        { name: 'remote_id', type: 'string', isIndexed: true },
        { name: 'title', type: 'string' },
        { name: 'description', type: 'string' },
        { name: 'specialty_name', type: 'string' },
        { name: 'is_fundamental', type: 'boolean' },
        { name: 'synced_at', type: 'number' },
      ],
    }),
    tableSchema({
      name: 'lessons',
      columns: [
        { name: 'remote_id', type: 'string', isIndexed: true },
        { name: 'module_id', type: 'string', isIndexed: true },
        { name: 'title', type: 'string' },
        { name: 'content', type: 'string' },
        { name: 'order_index', type: 'number' },
        { name: 'synced_at', type: 'number' },
      ],
    }),
    tableSchema({
      name: 'flashcards',
      columns: [
        { name: 'remote_id', type: 'string', isIndexed: true },
        { name: 'module_id', type: 'string', isIndexed: true },
        { name: 'front', type: 'string' },
        { name: 'back', type: 'string' },
        { name: 'due_date', type: 'number' },
        { name: 'interval', type: 'number' },
        { name: 'ease_factor', type: 'number' },
        { name: 'repetitions', type: 'number' },
        { name: 'pending_review', type: 'boolean' },
        { name: 'pending_quality', type: 'number', isOptional: true },
        { name: 'synced_at', type: 'number' },
      ],
    }),
    tableSchema({
      name: 'ai_messages',
      columns: [
        { name: 'conversation_id', type: 'string', isIndexed: true },
        { name: 'role', type: 'string' },
        { name: 'content', type: 'string' },
        { name: 'created_at', type: 'number' },
        { name: 'synced', type: 'boolean' },
      ],
    }),
  ],
});
