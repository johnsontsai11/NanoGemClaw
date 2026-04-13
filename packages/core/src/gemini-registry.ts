import type { ParseableSchema } from './types.js';

/** Registry mapping tool names to their input schemas for validation */
const inputSchemaRegistry = new Map<string, ParseableSchema>();

/** Register an input schema for a tool. Called during plugin tool registration. */
export function registerInputSchema(
  toolName: string,
  schema: ParseableSchema,
): void {
  inputSchemaRegistry.set(toolName, schema);
}

/** Clear all registered input schemas. */
export function clearInputSchemaRegistry(): void {
  inputSchemaRegistry.clear();
}

/** Get a registered input schema for a tool. */
export function getInputSchema(toolName: string): ParseableSchema | undefined {
  return inputSchemaRegistry.get(toolName);
}
