import {
  BarChart3,
  BookOpen,
  Calendar,
  Mail,
  MessageSquare,
  Palette,
  PenLine,
  Search,
  Smartphone,
  Target,
} from "lucide-react";

import type { ChatItem, NavItem, QuickAction } from "./types";

export const tools: NavItem[] = [
  { id: "assistant", label: "Chat", icon: MessageSquare },
  { id: "content", label: "Content Studio", icon: PenLine },
  { id: "seo", label: "SEO Keywords", icon: BarChart3 },
  { id: "email", label: "Email Campaigns", icon: Mail },
  { id: "social", label: "Social Media", icon: Smartphone },
  { id: "ads", label: "Ad Copy", icon: Target },
];

export const library: NavItem[] = [
  { id: "guidelines", label: "Brand Guidelines", icon: BookOpen },
  { id: "assets", label: "Asset Library", icon: Palette },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
];

export const initialChats: ChatItem[] = [
  {
    id: "launch",
    title: "Product Launch Support",
    meta: "Active - 12 messages",
    status: "active",
    starred: true,
  },
  {
    id: "audit",
    title: "SEO Audit Questions",
    meta: "Draft - 3 messages",
    status: "draft",
    starred: false,
  },
  {
    id: "social",
    title: "Social Calendar Ideas",
    meta: "Active - 8 messages",
    status: "active",
    starred: false,
  },
];

export const quickActions: QuickAction[] = [
  {
    title: "Generate Ad Copy",
    description: "Create high-converting ads for Google, Facebook, or LinkedIn",
    icon: Target,
    prompt: "Write Google Ads for a fitness app targeting millennials",
  },
  {
    title: "Content Calendar",
    description: "Plan your social media and blog content strategy",
    icon: Calendar,
    prompt: "Create a content calendar for a B2B SaaS company",
  },
  {
    title: "SEO Optimization",
    description: "Improve rankings with keyword suggestions and meta tags",
    icon: Search,
    prompt: "Optimize this headline for SEO: Best Coffee Makers 2024",
  },
  {
    title: "Email Sequence",
    description: "Build nurture campaigns and newsletters",
    icon: Mail,
    prompt: "Write a welcome email series for new subscribers",
  },
];

export const botResponses = [
  "Great brief! I'll create conversion-focused copy that highlights your USPs while maintaining a professional yet approachable tone. Here are three variations...",
  "Perfect! Based on current trends, I recommend focusing on long-tail keywords with high commercial intent. Here's your optimized strategy...",
  "Excellent idea! For this email sequence, I suggest a 5-touch nurture campaign. Subject line A/B tests show 'Unlock your' performs better. Here's the flow...",
  "Strategic thinking! For this campaign, let's segment your audience into three buckets: Awareness, Consideration, and Decision. Here's the content matrix...",
];

export const brandVoices = [
  "Professional + Friendly",
  "Bold + Energetic",
  "Luxury + Sophisticated",
  "Casual + Witty",
];
