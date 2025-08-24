# Git Workflow for KohTravel MVP

## 🌳 Branch Strategy

```
main (production)
 │
 └── mvp-development (MVP main branch)
      ├── phase-1-foundation
      ├── phase-2-document-processing  
      ├── phase-3-document-management
      ├── phase-4-chat-interface
      ├── phase-5-polish-security
      └── phase-6-testing-deployment
```

## 📋 Phase Development Process

### 1. Create Phase Branch
```bash
git checkout mvp-development
git pull origin mvp-development
git checkout -b phase-1-foundation
```

### 2. Work on Phase Tasks
- Complete all subtasks in the phase
- Test according to phase criteria
- Commit regularly with clear messages

### 3. Create Pull Request
```bash
git push origin phase-1-foundation
# Create PR: phase-1-foundation → mvp-development
```

### 4. Phase Review Checklist
- [ ] All phase tasks completed
- [ ] Programmatic tests pass
- [ ] Manual testing criteria met
- [ ] Code review approved
- [ ] No breaking changes to previous phases

### 5. Merge to MVP Development
- After approval, merge PR
- Delete phase branch
- Move to next phase

### 6. Final MVP Merge
```bash
# When all phases complete:
# Create PR: mvp-development → main
```

## 🧪 Testing Strategy

### Programmatic Tests
- Unit tests for core functions
- Integration tests for API endpoints
- Database migration tests
- Build/deployment tests

### Manual Testing Criteria
- User flows work as expected
- UI/UX is functional and intuitive
- Error handling works properly
- Performance is acceptable

## 📝 PR Template

```markdown
## Phase X: [Phase Name]

### ✅ Completed Tasks
- [ ] Task 1.1 - Description
- [ ] Task 1.2 - Description
- [ ] Task 1.3 - Description

### 🧪 Testing Criteria Met
**Programmatic:**
- [ ] All tests pass
- [ ] Build successful
- [ ] No breaking changes

**Manual:**
- [ ] Feature works as specified
- [ ] Error handling tested
- [ ] UI/UX reviewed

### 📱 How to Test
1. Step-by-step instructions
2. Expected results
3. Edge cases to verify

### 🔄 Next Phase Dependencies
- What the next phase will build on
- Any setup required for next phase
```