/**
 * IPC Handler: send-document
 * Sends a file as a document attachment to the current chat.
 */

import fs from 'fs';
import path from 'path';
import { InputFile } from 'grammy';
import type { IpcContext, IpcHandler } from '../types.js';
import { getBot } from '../state.js';
import { logger } from '../logger.js';
import { formatError } from '../utils.js';

export interface SendDocumentParams {
  file_path: string;
  caption?: string;
}

export async function handleSendDocument(
  params: SendDocumentParams,
  ctx: IpcContext,
): Promise<{ success: boolean; message?: string; error?: string }> {
  const { file_path, caption } = params;

  try {
    // Validate file exists
    if (!file_path) {
      return { success: false, error: 'file_path is required' };
    }

    if (!fs.existsSync(file_path)) {
      return {
        success: false,
        error: `File not found: ${file_path}`,
      };
    }

    // Get file stats
    const stats = fs.statSync(file_path);
    if (!stats.isFile()) {
      return {
        success: false,
        error: `Path is not a file: ${file_path}`,
      };
    }

    // Check file size (Telegram limit is 50MB for bots)
    const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
    if (stats.size > MAX_FILE_SIZE) {
      return {
        success: false,
        error: `File too large: ${(stats.size / 1024 / 1024).toFixed(2)}MB (max 50MB)`,
      };
    }

    // Prefer bot from IpcContext (available in fast-path), fall back to global singleton
    const bot = (ctx as any).bot ?? getBot();
    if (!bot) {
      return { success: false, error: 'Bot instance is not available' };
    }

    // Defensive check: ensure registeredGroups is a valid, non-null object
    if (!ctx || !ctx.registeredGroups || typeof ctx.registeredGroups !== 'object') {
      return { success: false, error: 'IPC context is missing registeredGroups' };
    }

    logger.debug(
      { sourceGroup: ctx.sourceGroup, groupFolder: (params as any).groupFolder },
      'send_document: resolving target group',
    );

    // Resolve target chat ID from context — guard against undefined group entries
    const targetGroupEntry = Object.entries(ctx.registeredGroups).find(
      ([, g]) => {
        if (!g) return false; // skip undefined/null entries in the map
        return (
          g.folder === (params as any).groupFolder ||
          g.folder === (params as any).group ||
          g.folder === ctx.sourceGroup
        );
      },
    );

    if (!targetGroupEntry) {
      logger.warn(
        {
          sourceGroup: ctx.sourceGroup,
          groupFolder: (params as any).groupFolder,
          knownGroups: Object.values(ctx.registeredGroups)
            .filter(Boolean)
            .map((g: any) => g.folder),
        },
        'send_document: could not resolve target group',
      );
      return {
        success: false,
        error: `Could not resolve target group for document send (sourceGroup=${ctx.sourceGroup}).`,
      };
    }

    const chatId = targetGroupEntry[0];
    const fileName = path.basename(file_path);

    // Send document
    await bot.api.sendDocument(chatId, new InputFile(file_path), {
      caption: caption || fileName,
    });

    logger.info(
      { chatId, file: fileName },
      'Document sent successfully',
    );

    return {
      success: true,
      message: `Document sent: ${fileName}`,
    };
  } catch (err) {
    const formatted = formatError(err);
    logger.error(
      { err: formatted, file_path },
      'Failed to send document',
    );
    return {
      success: false,
      error: `Failed to send document: ${formatted.message}`,
    };
  }
}

/**
 * Exported handler for IPC registration
 */
export const SendDocumentHandler: IpcHandler = {
  type: 'send_document',
  handle: async (data: Record<string, any>, ctx: IpcContext) => {
    const params = data as SendDocumentParams;
    const result = await handleSendDocument(params, ctx);

    if (!result.success) {
      logger.error({ error: result.error }, 'send_document failed');
    }
  },
  requiredPermission: 'own_group',
};
