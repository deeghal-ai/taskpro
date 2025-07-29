# 🎬 Video Production Manager Implementation Request

Hi! I need help implementing a new **Video Production Manager** role in my Django-based project management system. This is a **well-defined requirement** with a comprehensive implementation guide already prepared.

## 📋 What I Need

I want to add a complete video production project management workflow for **outsourced live-action video projects** that's completely separate from my existing in-house 3D visualization project management system.

**Key Requirements:**
- ✅ **New Django App**: Create `video_production` app (don't modify existing `projects` app)
- ✅ **New User Role**: `VIDEO_PM` (Video Production Manager) 
- ✅ **Video Production Workflow**: Sales → Shoot → Multiple Cuts → Voiceover → Final Delivery
- ✅ **Complex Cut Management**: Track up to 7 video cut iterations with client feedback
- ✅ **Voiceover Workflow**: Script creation → approval → computerized VO → final recording
- ✅ **Vendor Management**: Managing external video production agencies
- ✅ **Clean Separation**: Completely separate from existing DPM/TEAM_MEMBER 3D workflows

## 🎥 Video Production Context

### Video Product Types
Our Housing Studio's video production division handles **live-action video content** outsourced to specialized video agencies:
- **Drone Video** - Aerial footage of real estate projects
- **Drone Interactive** - Interactive aerial presentations  
- **Area Wiki** - Neighborhood and location overview videos
- **Corporate Video** - Company and project promotional content
- **Explainer Video** - Educational content about projects/services
- **Social Media Videos** - Short-form content for social platforms
- **Project Review Video** - Client testimonial and project showcase content

### Video Production Status Workflow
Unlike our 3D visualization projects, video production follows a complex multi-stage approval process:

**Complete Status Flow:**
```
Sales Confirmation → Data Received → Shoot Done → 
1st Cut Delivery → 1st Cut Rework → 2nd Cut Delivered → 2nd Cut Rework → 
... (up to 7th Cut) ... → 
Voiceover Script Shared → Voiceover Script Approved → 
Video with Computerized VO Delivered → Changes After Computerized VO → 
Voiceover Approved for Final Recording → Final Video with Watermark Shared → 
Final Delivery
```

## 📖 Implementation Guide

I have a **comprehensive implementation guide** that covers:
- Complete technical specifications for video production workflow
- Phase-by-phase implementation plan
- Database models for cuts, voiceover scripts, and vendor management
- Service layer architecture for video production business logic
- Forms, views, and templates for video project management
- Security and testing considerations

**Please read the attached `outsource_implementation_guide.md` file carefully** - it contains all the technical details, business requirements, and implementation steps for the video production system.

## 🎯 My Goal

I want you to follow the guide systematically, starting with **Phase 1: Create New Django App** (`video_production`) and proceeding through each phase. The guide is comprehensive and should answer most questions you might have.

## 🔧 Current System Context

- **Django 5.1+ application** with service layer architecture
- **Existing domains**: 
  - **3D Visualization** (In-house): DPM + TEAM_MEMBER roles managing 3D renders
  - **Video Production** (Outsourced): NEW domain for live-action video projects
- **Team**: 3 DPMs managing 30 3D visualizers for complex in-house 3D projects
- **Database**: PostgreSQL with UUID primary keys and proper relationships

## 📝 What I Expect

1. **Follow the implementation guide** phase by phase
2. **Ask clarifying questions** if anything is unclear about video production workflows
3. **Test thoroughly** to ensure no impact on existing 3D visualization functionality
4. **Maintain code quality** and follow existing patterns
5. **Implement role-based security** properly for VIDEO_PM role

## 🚨 Important Notes

- **NEW DJANGO APP**: Create `video_production` app, don't modify `projects` app (3D visualization)
- **Video-specific models**: VideoCut, VoiceoverScript, VideoProject, etc.
- **Complex workflow**: Multiple cut iterations, voiceover cycles, watermark previews
- **Service layer pattern**: Follow the established architecture
- **Complete separation**: Video production functionality should be completely independent from 3D visualization

## 🎬 Key Video Production Features

- **Cut Management**: Track multiple video cut iterations (1st, 2nd, 3rd... up to 7th cut)
- **Voiceover Workflow**: Script creation → approval → computerized VO → final recording
- **Watermark Previews**: Client reviews watermarked versions before final delivery
- **Vendor Coordination**: Managing external video production agencies
- **Live Shoot Coordination**: Managing on-location video shoots

Let's implement this step by step! Please start with Phase 1 and let me know if you need any clarification from the implementation guide about the video production workflows.

---

**Note**: This is for **video production projects** (drone videos, corporate videos, etc.) managed by external agencies, NOT for 3D visualization projects which are handled in-house by our existing team. 