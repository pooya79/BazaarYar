import type { CompanyProfileResponse } from "@/shared/api/schemas/settings";

export type CompanyProfileDraft = {
  enabled: boolean;
  name: string;
  description: string;
};

export const emptyCompanyProfileDraft: CompanyProfileDraft = {
  enabled: true,
  name: "",
  description: "",
};

export function toCompanyProfileDraft(
  profile: CompanyProfileResponse,
): CompanyProfileDraft {
  return {
    enabled: profile.enabled,
    name: profile.name,
    description: profile.description,
  };
}
