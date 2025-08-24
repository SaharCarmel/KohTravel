# OAuth Provider Setup Instructions

## 🔧 Phase 1 Authentication Setup Complete

✅ **NextAuth.js installed and configured**  
✅ **Google and GitHub providers ready**  
✅ **Auth components created**  
✅ **Environment variables template created**  

## 🚨 **Required: OAuth App Registration**

To complete the authentication setup, you need to create OAuth applications:

### 1. GitHub OAuth App
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. **Application name**: `KohTravel Development`
4. **Homepage URL**: `http://localhost:3002`
5. **Authorization callback URL**: `http://localhost:3002/api/auth/callback/github`
6. Copy the **Client ID** and **Client Secret**

### 2. Google OAuth App  
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable Google+ API
4. Go to Credentials → Create credentials → OAuth 2.0 Client IDs
5. **Application type**: Web application
6. **Authorized redirect URIs**: `http://localhost:3002/api/auth/callback/google`
7. Copy the **Client ID** and **Client Secret**

### 3. Update Environment Variables
Edit `/frontend/.env.local`:
```bash
GITHUB_ID=your-actual-github-client-id
GITHUB_SECRET=your-actual-github-client-secret
GOOGLE_CLIENT_ID=your-actual-google-client-id  
GOOGLE_CLIENT_SECRET=your-actual-google-client-secret
```

## 🧪 **Testing**
After setting up OAuth apps:
1. Restart development server: `npm run dev`
2. Visit `http://localhost:3002`
3. Click "GitHub" or "Google" buttons
4. Should redirect to OAuth provider
5. After authorization, redirect back to app

## 📋 **Phase 1 Status**
- ✅ Database setup (Railway PostgreSQL)
- ✅ Authentication setup (NextAuth.js)
- ⏳ OAuth provider registration (manual step)
- ⏳ End-to-end auth testing

**Next**: Complete OAuth setup, then move to Phase 2 (Document Upload)