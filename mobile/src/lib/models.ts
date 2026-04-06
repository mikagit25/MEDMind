/**
 * WatermelonDB models
 */
import { Model } from '@nozbe/watermelondb';
import { field, date, readonly } from '@nozbe/watermelondb/decorators';

export class ModuleModel extends Model {
  static table = 'modules';

  @field('remote_id') remoteId!: string;
  @field('title') title!: string;
  @field('description') description!: string;
  @field('specialty_name') specialtyName!: string;
  @field('is_fundamental') isFundamental!: boolean;
  @readonly @date('synced_at') syncedAt!: Date;
}

export class LessonModel extends Model {
  static table = 'lessons';

  @field('remote_id') remoteId!: string;
  @field('module_id') moduleId!: string;
  @field('title') title!: string;
  @field('content') content!: string;
  @field('order_index') orderIndex!: number;
  @readonly @date('synced_at') syncedAt!: Date;
}

export class FlashcardModel extends Model {
  static table = 'flashcards';

  @field('remote_id') remoteId!: string;
  @field('module_id') moduleId!: string;
  @field('front') front!: string;
  @field('back') back!: string;
  @date('due_date') dueDate!: Date;
  @field('interval') interval!: number;
  @field('ease_factor') easeFactor!: number;
  @field('repetitions') repetitions!: number;
  @field('pending_review') pendingReview!: boolean;
  @field('pending_quality') pendingQuality!: number | null;
  @readonly @date('synced_at') syncedAt!: Date;
}

export class AIMessageModel extends Model {
  static table = 'ai_messages';

  @field('conversation_id') conversationId!: string;
  @field('role') role!: string;
  @field('content') content!: string;
  @date('created_at') createdAt!: Date;
  @field('synced') synced!: boolean;
}
