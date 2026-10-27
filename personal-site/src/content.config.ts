import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: z.object({
    title: z.string(), description: z.string(), date: z.coerce.date(),
    category: z.string(), readingMinutes: z.number().positive(),
    sample: z.boolean().default(false), featured: z.boolean().default(false),
  }),
});
const projects = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/projects' }),
  schema: z.object({
    title: z.string(), description: z.string(), number: z.string(),
    status: z.string(), type: z.string(), year: z.string(),
    repository: z.string().url().optional(),
  }),
});
export const collections = { posts, projects };
