# Test Review — worked rubric examples

Concrete ✗/✓ pairs for the rubric in [../SKILL.md](../SKILL.md). Section numbers match the rubric's numbering. Principle 15 (*never recommend adding tests*) is a standing constraint with no code shape of its own, so it has no example here.

Snippets are TypeScript/Jest; the principles are framework-independent. Every ✓ shows the **shape** of a verdict, not a template to paste — a `Rewrite:` verdict must name the actual rename/restructuring for the code in the diff.

**Note what several of these examples have as their ✓: nothing at all.** For §1 and §12 the correct output is a `Delete` verdict — the improved version of the test is its absence. Reach for a rewrite only when the test can genuinely fail *and* no sibling already covers the behavior.

---

## 1. Vacuous / pass-through tests

```ts
// ✗ asserts what the type signature already guarantees
it('returns a string', () => {
  expect(typeof formatMemberName(aMember())).toBe('string');
});

// ✗ pass-through: the argument handed in is echoed back as the expectation.
//   No branching, no edge case — this only proves the function body was typed correctly.
it('passes the id to the repository', () => {
  service.getMember(7);
  expect(repo.findById).toHaveBeenCalledWith(7);
});
```

There is no ✓ rewrite for these — **`Delete` is the verdict**, and it is complete on its own. Neither one can go red under any change to `formatMemberName` or `getMember`, so removing them costs nothing. Writing a better test of that code in their place would be recommending a new test, which principle 15 forbids: delete and stop. (The second also violates principle 5 — an interaction assertion. Report it once, under whichever principle better explains why it's worthless.)

---

## 2. Tautological expectations

The expectation must not be computed the way the implementation computes it.

```ts
// ✗ the expected value is assembled the same way the code assembles it
expect(formatMemberName(member)).toBe(`${member.firstName} ${member.lastName}`);

// ✓ independent literal — this can disagree with the code
expect(formatMemberName({ firstName: 'Dana', lastName: 'Levi' })).toBe('Dana Levi');
```

The same trap, one step removed — both sides read the same source of truth:

```ts
// ✗ if STATUS_LABELS is wrong, the test is wrong in exactly the same way
expect(labelFor(Status.Rejected)).toBe(STATUS_LABELS[Status.Rejected]);

// ✓
expect(labelFor(Status.Rejected)).toBe('Rejected');
```

Watch for the same pattern in `reduce`/`map`/`sort` expectations and in hand-derived snapshots.

---

## 3. Over-mocked paths

```ts
// ✗ every step of the path is stubbed, so the assertion is decided before inviteMember runs.
//   No change to the eligibility rule or the invite shape can turn this red.
jest.spyOn(service, 'loadMember').mockResolvedValue(anActiveMember);
jest.spyOn(service, 'isEligibleForInvite').mockReturnValue(true);
jest.spyOn(service, 'buildInvite').mockReturnValue(anInvite);

expect(await service.inviteMember(memberId)).toBe(anInvite);

// ✓ stub only the boundary; the eligibility rule and the invite construction run for real
const membersApi = { fetchMember: jest.fn().mockResolvedValue(anActiveMember) };

expect(await createService({ membersApi }).inviteMember(memberId)).toEqual({
  memberId,
  invitedBy: 'community',
  expiresAt: '2026-08-02T00:00:00.000Z',
});
```

The tell: count what is *not* stubbed between the call and the assertion. If it's only the `return` statement, there is nothing under test.

---

## 4. Testing a copy of the code

```ts
// ✗ FakeCommunityPolicy re-implements the rule it claims to verify.
//   CommunityPolicy is never constructed, so a bug in it stays invisible forever.
class FakeCommunityPolicy {
  canInvite(member: Member) {
    return member.role === 'leader' || member.role === 'admin';   // copied from CommunityPolicy
  }
}

expect(new FakeCommunityPolicy().canInvite(aLeader)).toBe(true);

// ✓ construct the real policy; fake only what it reaches out to
expect(new CommunityPolicy(anOrgWithInvitesEnabled).canInvite(aLeader)).toBe(true);
```

**How to spot it in a diff:** a method body in the test file that reads like a paraphrase of the production method being tested. Grep the production symbol — if its logic appears in both files, the test is asserting against the copy.

Not the same thing: an in-memory fake of an *external* system (see §5). Reimplementing a slice of Mongo's `$in` semantics inside a fake model is fine — Mongo isn't the code under test. Reimplementing our own filtering rule is not.

---

## 5. Reaching past the interface — private methods

```ts
// ✗ casts past the type system to call a private method directly
class PricingService {
  calculateTotal(items: Item[]) { /* ... */ }
  private applyDiscount(total: number, code: string) { /* ... */ }
}

expect((service as any).applyDiscount(100, 'SUMMER10')).toBe(90);

// ✓ narrow it to `protected`, then forward to it through a spec-only mirror subclass
class PricingService {
  calculateTotal(items: Item[]) { /* ... */ }
  protected applyDiscount(total: number, code: string) { /* ... */ }
}

class PricingServiceUnderTest extends PricingService {
  exposedApplyDiscount(total: number, code: string) {
    return this.applyDiscount(total, code);
  }
}

expect(new PricingServiceUnderTest().exposedApplyDiscount(100, 'SUMMER10')).toBe(90);
```

This is the fix specifically for *calling* a private method — it's a different problem from *arranging state* on a private field, which stays a dependency-injection fix (see the private-field poke in the next section). Reach for the mirror-subclass escape hatch only after concluding the behavior can't reasonably be reached through the public API; `exposedApplyDiscount` must do nothing but forward the call, or the real fix is still injecting the collaborator.

---

## 5 + 7 + 8. Opaque → story → behavior

One example carried through three rewrites, because the first fix is not the last one. `batchUpdateMemberProfiles` sets an approval status on every community member matching a filter, minus the ones the admin deselected.

### ✗ Stage 1 — opaque literals, inline plumbing, interaction assertion

```ts
// To see why updated === 1 you must run it in your head: 2 members resolved,
// exclude 202 → only 201 survives → modifiedCount 1 → updated 1.
jest.spyOn(service, 'getMemberProfilesAndCount').mockResolvedValue([[{ userId: 201 }, { userId: 202 }], 2]);
const updateMany = jest.fn().mockResolvedValue({ modifiedCount: 1 });
(service as any).communitiesMembersModel = { updateMany };

const res = await service.batchUpdateMemberProfiles({
  communityId: 10, organizationId: 1, updates: { approvalStatus: 5 },
  filterBy: { role: 'member' }, excludedIds: [202],
});

expect(updateMany).toHaveBeenCalledWith(
  { communityId: 10, 'userDetails.id': { $in: [201] } }, { $set: { approvalStatus: 5 } });
expect(res).toEqual({ updated: 1 });
```

Violates **7** (opaque coupled literals, mechanical inline plumbing), **8** (no scenario in the name), **5** (asserts on a mock call, mocks the service's own method, arranges via a private field), and **2** (`updated: 1` is just the `modifiedCount` the test seeded).

### ⚠ Stage 2 — a story, but still coupled to the implementation

```ts
const givenMembersMatchTheFilter = (userIds: number[]) =>
  jest.spyOn(service, 'getMemberProfilesAndCount')
    .mockResolvedValue([userIds.map((userId) => ({ userId })) as any, userIds.length]);
const spyOnMemberUpdates = (modifiedCount: number) => {
  const updateMany = jest.fn().mockResolvedValue({ modifiedCount });
  (service as any).communitiesMembersModel = { updateMany };
  return updateMany;
};

it('updates only the members left after the admin deselects one', async () => {
  const [keptMember, deselectedMember] = [201, 202];
  givenMembersMatchTheFilter([keptMember, deselectedMember]);
  const updateMany = spyOnMemberUpdates(1);

  const res = await service.batchUpdateMemberProfiles({ /* … excludedIds: [deselectedMember] */ });

  expect(updateMany).toHaveBeenCalledWith(
    { communityId: 10, 'userDetails.id': { $in: [keptMember] } }, { $set: { approvalStatus: REJECTED } });
  expect(res).toEqual({ updated: 1 });
});
```

Principles **7** and **8** are now satisfied — the body reads given → when → then, and the title states the scenario. **This is still a finding.** The assertion pins the exact Mongo query the service emits, so switching to `bulkWrite`, changing the field path, or splitting the update into batches breaks a green test without changing a single observable behavior. It also still fakes the service's own method and arranges through a private field.

### ✓ Stage 3 — the effect made observable

Give the service a real (in-memory) boundary through the framework's own injection, and assert on the state it ends up in:

```ts
class InMemoryMembersModel {
  constructor(private readonly docs: MemberDoc[]) {}

  async updateMany(filter: MemberFilter, { $set }: { $set: Partial<MemberDoc> }) {
    const matched = this.docs.filter((doc) => matchesMongoFilter(doc, filter));
    matched.forEach((doc) => Object.assign(doc, $set));
    return { modifiedCount: matched.length };
  }

  async find(filter: MemberFilter) {
    return this.docs.filter((doc) => matchesMongoFilter(doc, filter));
  }
}

const givenCommunityMembers = async (userIds: number[]) => {
  const membersModel = new InMemoryMembersModel(
    userIds.map((userId) => ({ userId, communityId, role: 'member', approvalStatus: PENDING })),
  );
  const moduleRef = await Test.createTestingModule({ providers: [CommunitiesMembersService] })
    .overrideProvider(getModelToken(CommunitiesMember.name))
    .useValue(membersModel)
    .compile();

  return { service: moduleRef.get(CommunitiesMembersService), membersModel };
};

it('rejects every member matching the filter except the one the admin deselected', async () => {
  const [keptMember, deselectedMember] = [201, 202];
  const { service, membersModel } = await givenCommunityMembers([keptMember, deselectedMember]);

  const res = await service.batchUpdateMemberProfiles({
    communityId, organizationId, updates: { approvalStatus: REJECTED },
    filterBy: { role: 'member' }, excludedIds: [deselectedMember],
  });

  expect(await membersModel.find({ approvalStatus: REJECTED }))
    .toEqual([expect.objectContaining({ userId: keptMember })]);
  expect(res).toEqual({ updated: 1 });
});
```

What changed that matters:

- **No interaction assertion.** The test says *the kept member ended up rejected and the deselected one didn't* — true regardless of which Mongo call the service uses to get there.
- **`getMemberProfilesAndCount` runs for real.** It was our own code; faking it removed the thing most likely to hold the bug.
- **No private-field poke.** The model arrives through `overrideProvider`, the same seam Nest already provides.
- **`updated: 1` stopped being tautological.** The fake *derives* `modifiedCount` from the filter instead of being told it, so a broken exclusion now makes the number wrong.

### 8. Names, in isolation

| ✗ | ✓ |
|---|---|
| `it('works')` | `it('rejects a member who is already in another community')` |
| `it('test batchUpdate 2')` | `it('leaves deselected members untouched')` |
| `it('calls paymentService.process')` | `it('confirms the order when payment succeeds')` |
| `it('returns MemberDto[]')` | `it('returns members sorted by last name')` |
| `it('happy path')` | `it('grants leader access when the invite is still valid')` |

Formula when nothing better suggests itself: *unit → scenario → expected result*.

---

## 6. Right test level

```ts
// ✗ a full testing module, a mocked model and an injector — to exercise a pure mapping
const moduleRef = await Test.createTestingModule({
  providers: [MembersService, { provide: getModelToken(Member.name), useValue: {} }],
}).compile();
const service = moduleRef.get(MembersService);

expect(service.toMemberDto(memberDoc)).toEqual({ id: 1, name: 'Dana Levi', role: 'member' });

// ✓ it's a pure function — call it
expect(toMemberDto(memberDoc)).toEqual({ id: 1, name: 'Dana Levi', role: 'member' });
```

Don't flag the reverse case: heavy setup that genuinely exercises wiring, transactions, or guard/interceptor behavior is earning its cost.

---

## 9. Describe blocks reference the unit's name

```ts
// ✗ hand-typed string — a rename-symbol refactor on calculateFollowingRunUtc won't touch this
describe('calculateFollowingRunUtc', () => {

// ✓ can't drift: renaming the method renames the describe block for free
describe(IntegrationScheduleRecurrenceService.prototype.calculateFollowingRunUtc.name, () => {
```

Same idea one level up, for the outer `describe` naming the class/function itself:

```ts
// ✗
describe('MembersCrudService', () => {

// ✓
describe(MembersCrudService.name, () => {
```

**Verdict: `Rewrite`**, and normally P3 — it's the more durable form, not a correctness fix. It escalates to P2 only when the literal has already drifted, e.g. `describe('calculateNextRun', ...)` for a method now called `calculateFollowingRunUtc`: at that point the block is actively misdescribing the suite.

Don't force this onto a `describe` that isn't naming one importable symbol — `describe('when the invite has expired', () => { ... })` groups a scenario, not a unit, and has nothing to hang `.name` off of. Leave it as a string.

---

## 10. One behavior per test

```ts
// ✗ three behaviors in one test. The name has to go vague, and the first
//   failure hides the other two.
it('handles member updates', async () => {
  expect(await service.batchUpdate(rejectAll)).toEqual({ updated: 3 });
  expect(await service.batchUpdate(withExclusion)).toEqual({ updated: 2 });
  await expect(service.batchUpdate(otherOrg)).rejects.toThrow(ForbiddenException);
});

// ✓ one scenario each, each honestly nameable
it('rejects every member matching the filter', …);
it('leaves deselected members untouched', …);
it('refuses a community owned by another organization', …);
```

Several `expect` lines describing one outcome are still one test — the assertion count isn't the measure.

---

## 11. Table-driven consolidation

```ts
// ✗ four tests differing only in input and expected output
it('labels a pending member as Pending', () => expect(labelFor(Status.Pending)).toBe('Pending'));
it('labels an active member as Active', () => expect(labelFor(Status.Active)).toBe('Active'));
it('labels a rejected member as Rejected', () => expect(labelFor(Status.Rejected)).toBe('Rejected'));
it('labels a removed member as Removed', () => expect(labelFor(Status.Removed)).toBe('Removed'));

// ✓ one table, one row per case that already existed, rows named in domain terms
it.each`
  scenario             | status             | label
  ${'awaiting review'} | ${Status.Pending}  | ${'Pending'}
  ${'approved'}        | ${Status.Active}   | ${'Active'}
  ${'turned down'}     | ${Status.Rejected} | ${'Rejected'}
  ${'removed'}         | ${Status.Removed}  | ${'Removed'}
`('labels a member $scenario as "$label"', ({ status, label }) => {
  expect(labelFor(status)).toBe(label);
});
```

Named rows (`$scenario`, `$label`) are the point — a positional `%s` table or an array of unlabelled tuples reports failures as "case 3" and undoes the readability the consolidation was for.

**The table must not grow.** Four tests in, four rows out. If `Status.Suspended` was never tested, it does not get a row — proposing one is recommending a new test, which principle 15 forbids.

---

## 12. Reduce toward fewer tests

§11 merges cases that differ. §12 removes cases that don't. Three tests, one code path:

```ts
// ✗ all three take the same branch of `canInvite`: role is not leader/admin.
//   The second and third add no path the first doesn't already walk.
it('does not let a member invite', () => expect(policy.canInvite(aMemberWith('member'))).toBe(false));
it('does not let a guest invite', () => expect(policy.canInvite(aMemberWith('guest'))).toBe(false));
it('returns false for an unknown role', () => expect(policy.canInvite(aMemberWith('visitor'))).toBe(false));
```

**Verdict: `Delete` the second and third** (`policy.spec.ts:41`, `policy.spec.ts:45`). Not "merge into a table" — a table of three rows that all exercise the same branch is the same redundancy with better formatting. One case for the branch is the whole point.

The test to ask about is whether a *different line of production code* runs. Same branch, different literal → surplus. Different branch → keep one of each.

A duplicate that straddles the diff:

```ts
// members.spec.ts:118 (untouched, already in the suite)
it('rejects an invite for a member of another organization', …);

// members.spec.ts:204 (added by this diff)
it('throws ForbiddenException when the org does not match', …);
```

**Verdict: `Delete` `members.spec.ts:204`** — same scenario as `members.spec.ts:118`, which the diff didn't touch. The finding lands on the new test and cites the old one as evidence. Never propose rewriting `:118`; it isn't in scope.

**There is no floor.** If every test a diff touched turns out to be surplus or unfailable, "delete all 7" is the correct report. Coverage percentage is not a reason to keep one alive — a test that can't fail was never covering anything to begin with.

---

## 13. Isolation and leakage

```ts
// ✗ a shared, mutated fixture: the second test only passes when it runs first
const member = { id: 1, roles: ['member'] };

it('starts out as a plain member', () => {
  expect(member.roles).toEqual(['member']);
});
it('promotes a member to leader', () => {
  promote(member);
  expect(member.roles).toContain('leader');
});

// ✓ build the state per test
const aMember = () => ({ id: 1, roles: ['member'] });
```

```ts
// ✗ the frozen clock and the spy leak into every later test in the file
jest.useFakeTimers().setSystemTime(new Date('2026-07-26'));
jest.spyOn(tokenService, 'sign').mockReturnValue('token');

// ✓ scope and revert them
afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();      // or `restoreMocks: true` / `resetMocks: true` in jest config
});
```

Also in scope: module-level caches and singletons carried between tests, unreverted `process.env` writes, and any real I/O in a unit test — an unmocked network call, the filesystem, real `Date.now()` or `Math.random()`. These are the first suspects behind a test that is slow, flaky, or order-dependent.

---

## 14. DTO/validation-schema tests

```ts
// ✗ every assertion here just confirms class-validator enforces the
//   decorators already declared on the DTO — nothing here is our logic.
export class BatchSetCommunitiesHubBundlesDto {
  @IsArray() @ArrayNotEmpty() @IsInt({ each: true })
  readonly communityIds: number[];
  @IsArray() @ArrayNotEmpty() @IsString({ each: true })
  readonly bundleKeys: string[];
}

describe(BatchSetCommunitiesHubBundlesDto.name, () => {
  const errorsFor = (payload: unknown) => validateSync(plainToClass(BatchSetCommunitiesHubBundlesDto, payload));

  it('rejects an empty communityIds array', () => {
    expect(errorsFor({ ...validPayload, communityIds: [] }).some((e) => e.property === 'communityIds')).toBe(true);
  });
  // …and five more like it, one per decorator
});
```

There is no ✓ rewrite — **`Delete` all six**. Removing `@ArrayNotEmpty()` would still turn the real request red at the controller, just via the pipe's actual `400`, not via a hand-called `validateSync`. Nothing here earns a dedicated suite.

Exception: a DTO with a hand-written `@ValidatorConstraint` or a `@Transform` that computes something (not just reshapes types) has real logic — keep the assertions on *that*, and drop the plain field-decorator ones around it.
