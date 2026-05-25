export type LabResultEntry = {
  id: number;
  test_category: string;
  test_type: string;
  collection_date: string;
  titer: string | null;
  result: string | null;
};

export type LabResultEntryWriteInput = Partial<LabResultEntry> & {
  id?: number;
};

export type LabResultEntryRead = LabResultEntry;
