import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ImageSearchListComponent } from './image-search-list.component';

describe('ImageSearchListComponent', () => {
  let component: ImageSearchListComponent;
  let fixture: ComponentFixture<ImageSearchListComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ImageSearchListComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ImageSearchListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
