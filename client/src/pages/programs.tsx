import { PageHeader } from "../components/page-header";
import { AddProgramButton } from "../features/programs/add-program-button";
import { ProgramList } from "../features/programs/program-list";

export function Programs() {
  return (
    <>
      <PageHeader title="תוכניות">
        <AddProgramButton />
      </PageHeader>
      <ProgramList />
    </>
  );
}
