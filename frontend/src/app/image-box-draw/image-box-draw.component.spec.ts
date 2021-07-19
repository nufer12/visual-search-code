import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ImageBoxDrawComponent } from './image-box-draw.component';

describe('ImageBoxDrawComponent', () => {
  let component: ImageBoxDrawComponent;
  let fixture: ComponentFixture<ImageBoxDrawComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ImageBoxDrawComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ImageBoxDrawComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
