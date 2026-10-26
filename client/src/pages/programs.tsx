import { PageHeader } from "../components/page-header";
import { AddProgramButton } from "../features/programs/add-program-button";
import { MasterXlsxActions } from "../features/programs/master-xlsx-actions";
import { ProgramList } from "../features/programs/program-list";

export function Programs() {
  return (
    <>
      <PageHeader title="תוכניות">
        <div className="flex flex-wrap gap-2">
          <MasterXlsxActions />
          <AddProgramButton />
        </div>
      </PageHeader>
      <ProgramList />
    </>
  );
}
