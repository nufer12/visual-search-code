import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ImageSearchToolComponent } from './image-search-tool.component';

describe('ImageSearchToolComponent', () => {
  let component: ImageSearchToolComponent;
  let fixture: ComponentFixture<ImageSearchToolComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ImageSearchToolComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ImageSearchToolComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
